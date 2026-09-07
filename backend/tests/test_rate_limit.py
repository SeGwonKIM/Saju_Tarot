"""레이트리밋 (PRD §12.5).

집 PC 를 인터넷에 공개하면 이게 없을 때 요금이 그대로 나간다 (§17).
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import rate_limit
from app.main import app

client = TestClient(app)

BODY = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "solar",
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "birth_place": "서울",
    "topics": ["연애"],
    "tarot_mode": "auto",
}


@pytest.fixture(autouse=True)
def clean():
    rate_limit.reset()
    yield
    rate_limit.reset()


# 돈이 드는 창구는 풀이 생성 하나뿐이다 (v3.0). 계산은 공짜라 세지 않는다.
#
# 없는 id 를 부른다. 레이트리밋은 미들웨어라 핸들러보다 **먼저** 돌기 때문에,
# 통과하면 404, 막히면 429 가 온다. LLM 을 부르지 않으므로 테스트가 요금을
# 쓰지도, 네트워크를 타지도 않는다.
NOT_FOUND = 404


def post(ip: str = "1.2.3.4"):
    return client.post(
        "/api/v1/readings/r-nonexistent/report", headers={"X-Forwarded-For": ip}
    )


def test_allows_up_to_the_limit():
    for i in range(rate_limit.PER_IP_LIMIT):
        assert post().status_code == NOT_FOUND, f"{i + 1}번째가 막혔다"


def test_blocks_after_limit():
    for _ in range(rate_limit.PER_IP_LIMIT):
        post()
    r = post()
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["Retry-After"]) > 0


def test_limit_is_per_ip():
    """한 사람이 막혀도 다른 손님은 쓸 수 있어야 한다."""
    for _ in range(rate_limit.PER_IP_LIMIT):
        post(ip="1.1.1.1")
    assert post(ip="1.1.1.1").status_code == 429
    assert post(ip="2.2.2.2").status_code == NOT_FOUND


def test_global_limit_protects_the_bill():
    """IP 를 바꿔가며 때려도 전체 한도에서 멈춘다."""
    for i in range(rate_limit.GLOBAL_LIMIT):
        post(ip=f"10.0.{i // 250}.{i % 250}")
    assert post(ip="9.9.9.9").status_code == 429


def test_calculation_is_not_limited():
    """계산은 공짜다 — 한도의 세 배를 불러도 막히면 안 된다 (v3.0).

    예전에는 `POST /readings` 도 셌다. 그때는 이 호출이 곧 LLM 호출이었기
    때문이다. 지금은 계산만 하므로, 세면 손님이 실제 쓴 것보다 빨리 막힌다.
    """
    for i in range(rate_limit.PER_IP_LIMIT * 3):
        r = client.post(
            "/api/v1/readings", json=BODY, headers={"X-Forwarded-For": "3.3.3.3"}
        )
        assert r.status_code == 201, f"{i + 1}번째 계산이 막혔다"
        assert r.json()["report"] is None, "계산 호출은 풀이를 만들지 않는다"


def test_reads_are_not_limited():
    """조회·헬스체크는 비용이 안 드니 죄지 않는다."""
    for _ in range(rate_limit.PER_IP_LIMIT + 5):
        assert client.get("/api/v1/health").status_code == 200
    for _ in range(rate_limit.PER_IP_LIMIT + 5):
        r = client.post(
            "/api/v1/calendar/convert",
            json={"calendar_type": "solar", "date": "1990-01-01"},
        )
        assert r.status_code == 200


def _req(headers: dict[str, str], peer: str | None = None):
    class Req:
        pass

    r = Req()
    r.headers = {k.lower(): v for k, v in headers.items()}
    r.client = type("C", (), {"host": peer})() if peer else None
    return r


def test_forwarded_header_is_used():
    """터널 뒤에서는 실제 주소가 헤더로 온다 — **맨 뒤** 값이다.

    맨 앞자리는 요청자가 직접 채울 수 있다. 앞단 프록시는 자기가 받은 주소를
    뒤에 덧붙이므로, 믿을 수 있는 건 마지막 항목이다.
    """
    ip = rate_limit.client_ip(_req({"x-forwarded-for": "203.0.113.7, 10.0.0.1"}))
    assert ip == "10.0.0.1"


def test_forwarded_header_cannot_be_spoofed():
    """헤더를 바꿔가며 IP당 제한을 우회하지 못해야 한다.

    Cloudflare 는 CF-Connecting-IP 를 **덮어쓴다**. 요청자가 무엇을 넣든
    실제 주소로 집계되어 같은 바구니에 들어간다.
    """
    real = "1.2.3.4"
    attempts = [
        {"cf-connecting-ip": real, "x-forwarded-for": "9.9.9.9, " + real},
        {"cf-connecting-ip": real, "x-forwarded-for": "8.8.8.8, " + real},
        {"cf-connecting-ip": real},
    ]
    assert {rate_limit.client_ip(_req(h)) for h in attempts} == {real}


def test_direct_connection_uses_socket():
    """프록시가 없는 구성(내 PC·같은 와이파이)은 소켓 주소를 쓴다."""
    assert rate_limit.client_ip(_req({}, peer="192.168.0.9")) == "192.168.0.9"


def test_oversized_body_is_rejected():
    """큰 본문 하나로 집 PC 메모리를 고갈시키지 못하게 한다 (PRD §12.5).

    uvicorn 에는 기본 상한이 없어서 공개 서버에서는 DoS 통로가 된다.
    """
    huge = {**BODY, "name": "가" * 200_000}
    r = client.post("/api/v1/readings", json=huge)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_normal_body_passes():
    assert client.post("/api/v1/readings", json=BODY).status_code == 201


# ── 하루 상한 (PRD §11.3 "일 호출 상한 + 초과 시 429") ──────────────
#
# 시간당 한도만 있으면 하루가 열려 있다 — 100건/시간 × 24시간 × 50원 ≈ 하루 12만원.
# 다만 하루 한도는 시간당 한도보다 **느슨해야** 하므로(그래야 시간당 한도가 살아 있다)
# 빠른 루프로는 시간당 한도가 먼저 걸려 도달할 수 없다.
# 그래서 하루 집계를 직접 채워 놓고 그다음 요청을 확인한다.


def test_daily_limit_is_looser_than_hourly():
    """하루 한도가 시간당 한도보다 촘촘하면 시간당 한도가 죽은 코드가 된다."""
    assert rate_limit.DAILY_GLOBAL_LIMIT >= rate_limit.GLOBAL_LIMIT
    assert rate_limit.DAILY_PER_IP_LIMIT >= rate_limit.PER_IP_LIMIT


def test_daily_global_limit_blocks_with_its_own_message():
    """하루치를 다 쓰면 막고, 문구가 "잠시 후"가 아니라 자정 안내여야 한다."""
    rate_limit._roll_day(datetime.now(rate_limit.KST))
    rate_limit._day_global = rate_limit.DAILY_GLOBAL_LIMIT

    r = post(ip="9.9.9.9")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "DAILY_LIMIT_EXCEEDED"
    msg = r.json()["error"]["message"]
    assert "실행 한도" in msg
    assert "자정" in msg
    assert "잠시 후 다시 시도" not in msg
    assert int(r.headers["Retry-After"]) > 0


def test_daily_per_ip_limit_spares_other_guests():
    """한 사람이 하루치를 다 써도 다른 손님은 쓸 수 있어야 한다."""
    rate_limit._roll_day(datetime.now(rate_limit.KST))
    rate_limit._day_per_ip["5.5.5.5"] = rate_limit.DAILY_PER_IP_LIMIT

    blocked = post(ip="5.5.5.5")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "DAILY_LIMIT_EXCEEDED"
    assert post(ip="6.6.6.6").status_code != 429


def test_day_rolls_over_at_kst_midnight():
    """자정이 지나면 하루치가 새로 시작한다 — 어제 한도가 오늘을 막지 않는다."""
    rate_limit._roll_day(datetime.now(rate_limit.KST) - timedelta(days=1))
    rate_limit._day_global = rate_limit.DAILY_GLOBAL_LIMIT

    rate_limit._roll_day(datetime.now(rate_limit.KST))
    assert rate_limit._day_global == 0
    assert post(ip="7.7.7.7").status_code != 429


def test_retry_after_points_at_midnight():
    """하루 한도의 Retry-After 는 자정까지 남은 초다 (최대 24시간)."""
    secs = rate_limit._until_midnight(datetime.now(rate_limit.KST))
    assert 0 < secs <= 86401


def test_daily_limit_does_not_touch_the_write_path():
    """쓰기(계산·공유)는 돈이 안 든다 — 하루 요금 한도에 닳지 않아야 한다."""
    rate_limit._roll_day(datetime.now(rate_limit.KST))
    before = rate_limit._day_global
    client.post("/api/v1/readings", json=BODY, headers={"X-Forwarded-For": "4.4.4.4"})
    assert rate_limit._day_global == before
