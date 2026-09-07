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
from datetime import datetime, timedelta, timezone

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

# 계산 창구(POST /readings)는 돈은 안 들지만 **쓰기**다. 한 번마다 DB 에 행이
# 쌓이므로 무제한으로 두면 디스크를 채워 서비스를 멈출 수 있다.
# v3.0 에서 레이트리밋을 /report 로 옮기면서 이쪽이 통째로 풀렸다(실측 20/20 통과).
# LLM 요금이 걸린 쪽보다는 느슨하게, 그러나 도배는 막히게 둔다.
WRITE_PREFIX = "/api/v1/readings"
WRITE_PER_IP_LIMIT = 30

# IP당만 세면 **전체는 무제한**이다 — 요금 경로에는 GLOBAL_LIMIT 이 있는데 이쪽에는
# 없었다. IP 를 바꿔가며 넣으면 그대로 통과한다(점검에서 발견).
# 리포트 1건이 약 5KB 라, 하루 상한이 없으면 쓰레기 행이 계속 쌓여 조회가 느려지고
# 백업도 무거워진다. 실사용은 하루 10건 남짓이라 아래 값도 넉넉하다.
#   최악의 경우 = DAILY_WRITE_GLOBAL_LIMIT × 5KB ≈ 하루 2.5MB
WRITE_GLOBAL_LIMIT = 200
DAILY_WRITE_PER_IP_LIMIT = 60
DAILY_WRITE_GLOBAL_LIMIT = 500

PER_IP_LIMIT = 10
GLOBAL_LIMIT = 100

# 하루 상한 (PRD §11.3 "일 호출 상한 + 초과 시 429").
# 시간당 한도만 있으면 **하루가 열려 있다** — 100건/시간 × 24시간 × 50원 ≈ 하루 12만원.
# 실사용은 하루 10건 남짓이라 아래 값도 20배 여유다. 요금이 걱정되면 낮춘다.
#   최악의 경우 = DAILY_GLOBAL_LIMIT × 건당 약 50원
#
# ⚠️ 하루 한도는 시간당 한도보다 **느슨해야** 한다. 더 촘촘하면 시간당 한도가
#    영영 걸리지 않는 죽은 코드가 된다 (test_daily_limit_is_looser_than_hourly).
DAILY_PER_IP_LIMIT = 20
DAILY_GLOBAL_LIMIT = 200

_per_ip: dict[str, deque[float]] = defaultdict(deque)
_global: deque[float] = deque()

# 하루치는 흐르는 창이 아니라 **한국시간 달력 하루**로 센다.
# 사용자에게 "자정에 다시 열린다"고 말할 수 있어야 하기 때문이다.
KST = timezone(timedelta(hours=9))
_day = ""                                   # 집계 중인 KST 날짜 (YYYY-MM-DD)
_day_global = 0
_day_per_ip: dict[str, int] = defaultdict(int)
# 쓰기 바구니는 요금 바구니와 **따로** 둔다.
# 같이 세면 계산 몇 번에 풀이 한도가 닳아 버린다.
_writes: dict[str, deque[float]] = defaultdict(deque)
_writes_global: deque[float] = deque()
_day_writes_global = 0
_day_writes_per_ip: dict[str, int] = defaultdict(int)


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
    """LLM 요금이 드는 요청 — 풀이 생성 하나뿐이다."""
    return request.method in COSTLY_METHODS and request.url.path.endswith(COSTLY_SUFFIX)


def is_write(request: Request) -> bool:
    """돈은 안 들지만 DB 에 행을 남기는 요청 (계산·공유 링크 발급)."""
    return (
        request.method in COSTLY_METHODS
        and request.url.path.startswith(WRITE_PREFIX)
        and not is_costly(request)
    )


def check_write(request: Request) -> tuple[bool, int, str]:
    """쓰기 상한. 요금 한도와 따로 센다.

    IP당·전체를 모두 본다. 예전에는 IP당만 세서 IP 를 바꿔가면 전체가 무제한이었다.
    하루 상한도 함께 둔다 — 쓰레기 행이 쌓이면 조회가 느려지고 백업이 무거워진다.
    """
    now = time.monotonic()
    now_kst = datetime.now(KST)
    ip = client_ip(request)

    _roll_day(now_kst)

    global _day_writes_global
    if _day_writes_global >= DAILY_WRITE_GLOBAL_LIMIT:
        return False, _until_midnight(now_kst), "DAILY_WRITE_LIMIT_EXCEEDED"
    if _day_writes_per_ip[ip] >= DAILY_WRITE_PER_IP_LIMIT:
        return False, _until_midnight(now_kst), "DAILY_WRITE_LIMIT_EXCEEDED"

    _prune(_writes_global, now)
    if len(_writes_global) >= WRITE_GLOBAL_LIMIT:
        return False, int(WINDOW_SECONDS - (now - _writes_global[0])) + 1, "RATE_LIMITED"

    bucket = _writes[ip]
    _prune(bucket, now)
    if len(bucket) >= WRITE_PER_IP_LIMIT:
        return False, int(WINDOW_SECONDS - (now - bucket[0])) + 1, "RATE_LIMITED"

    bucket.append(now)
    _writes_global.append(now)
    _day_writes_per_ip[ip] += 1
    _day_writes_global += 1
    return True, 0, ""


def _roll_day(now_kst: datetime) -> None:
    """자정(KST)이 지나면 하루치 집계를 새로 시작한다 (요금·쓰기 둘 다)."""
    global _day, _day_global, _day_writes_global
    today = now_kst.date().isoformat()
    if today != _day:
        _day = today
        _day_global = 0
        _day_per_ip.clear()
        _day_writes_global = 0
        _day_writes_per_ip.clear()


def _until_midnight(now_kst: datetime) -> int:
    """다음 자정(KST)까지 남은 초. 하루 한도의 Retry-After 로 쓴다."""
    midnight = (now_kst + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((midnight - now_kst).total_seconds()) + 1


def check(request: Request) -> tuple[bool, int, str]:
    """(허용 여부, 재시도까지 남은 초, 막은 이유 코드).

    하루 한도를 먼저 본다 — 더 바깥쪽 울타리이고, 사용자에게 보여줄 안내도
    "잠시 후"가 아니라 "자정에 다시 열린다"로 달라지기 때문이다.
    """
    now = time.monotonic()
    now_kst = datetime.now(KST)
    ip = client_ip(request)

    _roll_day(now_kst)

    global _day_global
    if _day_global >= DAILY_GLOBAL_LIMIT:
        return False, _until_midnight(now_kst), "DAILY_LIMIT_EXCEEDED"
    if _day_per_ip[ip] >= DAILY_PER_IP_LIMIT:
        return False, _until_midnight(now_kst), "DAILY_LIMIT_EXCEEDED"

    _prune(_global, now)
    if len(_global) >= GLOBAL_LIMIT:
        return False, int(WINDOW_SECONDS - (now - _global[0])) + 1, "RATE_LIMITED"

    bucket = _per_ip[ip]
    _prune(bucket, now)
    if len(bucket) >= PER_IP_LIMIT:
        return False, int(WINDOW_SECONDS - (now - bucket[0])) + 1, "RATE_LIMITED"

    bucket.append(now)
    _global.append(now)
    _day_per_ip[ip] += 1
    _day_global += 1
    return True, 0, ""


def too_many(retry_after: int, code: str = "RATE_LIMITED") -> JSONResponse:
    """PRD §10.6 에러 규약 그대로.

    하루 한도는 문구가 다르다. 자정까지 몇 시간 남았을 수 있는데
    "잠시 후 다시 시도해 주세요"라고 하면 거짓 안내가 된다.
    """
    hours = retry_after // 3600
    when = f"약 {hours}시간 뒤" if hours >= 1 else "잠시 뒤"

    if code == "DAILY_LIMIT_EXCEEDED":
        message = (
            f"오늘 실행 한도({DAILY_GLOBAL_LIMIT}건)를 초과했습니다. "
            f"한국시간 자정({when})에 다시 열립니다."
        )
    elif code == "DAILY_WRITE_LIMIT_EXCEEDED":
        # 문구를 나눈다 — 이쪽은 풀이(돈 드는 것)가 아니라 계산·공유 요청이다
        message = (
            f"오늘 요청 한도({DAILY_WRITE_GLOBAL_LIMIT}건)를 초과했습니다. "
            f"한국시간 자정({when})에 다시 열립니다."
        )
    else:
        message = "요청이 많습니다. 잠시 후 다시 시도해 주세요."

    return JSONResponse(
        status_code=429,
        content={"error": {"code": code, "message": message}},
        headers={"Retry-After": str(retry_after)},
    )


def reset() -> None:
    """테스트용."""
    global _day, _day_global, _day_writes_global
    _per_ip.clear()
    _global.clear()
    _writes.clear()
    _writes_global.clear()
    _day = ""
    _day_global = 0
    _day_per_ip.clear()
    _day_writes_global = 0
    _day_writes_per_ip.clear()
