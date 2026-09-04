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
COSTLY_METHODS = {"POST"}
COSTLY_PREFIXES = ("/api/v1/readings",)

PER_IP_LIMIT = 10
GLOBAL_LIMIT = 100

_per_ip: dict[str, deque[float]] = defaultdict(deque)
_global: deque[float] = deque()


def client_ip(request: Request) -> str:
    """터널·프록시 뒤에서는 실제 주소가 헤더로 온다.

    ⚠️ 헤더는 위조할 수 있다. 우리 앞단(Cloudflare Tunnel 등)이 덧붙인 값만
    믿을 수 있으므로, 신뢰할 프록시가 없는 구성이라면 소켓 주소를 쓴다.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(bucket: deque[float], now: float) -> None:
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()


def is_costly(request: Request) -> bool:
    return request.method in COSTLY_METHODS and request.url.path.startswith(COSTLY_PREFIXES)


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
