"""레이트리밋 (PRD §12.5).

집 PC 를 인터넷에 공개하는 순간 반드시 필요해진다. 리포트 한 건마다 LLM 을
호출하므로, 누가 반복 요청하면 **요금이 그대로 나간다**(§17 요금 폭탄).

메모리에만 둔다 — 서버 하나짜리 구성이라 이걸로 충분하다.
서버를 여러 대로 늘리면 공유 저장소(Redis 등)로 옮겨야 한다.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("saju.ratelimit")

WINDOW_SECONDS = 3600

# 비용이 드는 경로만 죈다. 조회·헬스체크는 대상이 아니다.
#
# v3.0 에서 계산과 풀이를 갈랐다. 돈이 드는 것은 **풀이 생성 하나뿐**이다.
#   POST /readings              계산만 — 49ms, 공짜        → 안 센다
#   POST /readings/{id}/report  LLM 호출 — 건당 약 50원    → 센다
#   POST /readings/{id}/share   공유 링크 — 공짜           → 안 센다
# 예전처럼 prefix 로 죄면 계산·공유까지 세어 손님이 실제 쓴 것보다 빨리 막힌다.
COSTLY_METHODS = {"POST"}
COSTLY_SUFFIX = "/report"

PER_IP_LIMIT = 10
GLOBAL_LIMIT = 100

_per_ip: dict[str, deque[float]] = defaultdict(deque)
_global: deque[float] = deque()


def client_ip(request: Request) -> str:
    """터널·프록시 뒤에서는 실제 주소가 헤더로 온다.

    ⚠️ 헤더는 위조할 수 있다. **요청자가 넣은 값과 우리 앞단이 넣은 값을
    구분해야** 한다. 예전에는 X-Forwarded-For 의 맨 앞을 썼는데, 그 자리는
    요청자가 직접 채울 수 있다. 헤더만 바꿔가며 보내면 IP당 제한이 통째로
    무력화된다(점검에서 실제로 뚫렸다 — 11번째에 막혀야 할 요청이 통과했다).

    믿는 순서
      1) CF-Connecting-IP — Cloudflare 가 **덮어쓴다**. 요청자가 넣어도 지워진다
      2) X-Forwarded-For 의 **맨 뒤** — 바로 앞 프록시가 덧붙인 값이다.
         요청자가 앞쪽에 뭘 채워 넣든 마지막 자리는 우리 앞단이 쓴다
      3) 소켓 주소 — 프록시가 없는 구성(내 PC 직접 접속·같은 와이파이)
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]

    return request.client.host if request.client else "unknown"


def _prune(bucket: deque[float], now: float) -> None:
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()


def is_costly(request: Request) -> bool:
    return request.method in COSTLY_METHODS and request.url.path.endswith(COSTLY_SUFFIX)


def check(request: Request) -> tuple[bool, int]:
    """(허용 여부, 재시도까지 남은 초)."""
    now = time.monotonic()
    ip = client_ip(request)

    _prune(_global, now)
    if len(_global) >= GLOBAL_LIMIT:
        return False, int(WINDOW_SECONDS - (now - _global[0])) + 1

    bucket = _per_ip[ip]
    _prune(bucket, now)
    if len(bucket) >= PER_IP_LIMIT:
        return False, int(WINDOW_SECONDS - (now - bucket[0])) + 1

    bucket.append(now)
    _global.append(now)
    return True, 0


def too_many(retry_after: int) -> JSONResponse:
    """PRD §10.6 에러 규약 그대로."""
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "요청이 많습니다. 잠시 후 다시 시도해 주세요.",
            }
        },
        headers={"Retry-After": str(retry_after)},
    )


def reset() -> None:
    """테스트용."""
    _per_ip.clear()
    _global.clear()
