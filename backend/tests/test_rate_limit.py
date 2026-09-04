"""레이트리밋 (PRD §12.5).

집 PC 를 인터넷에 공개하면 이게 없을 때 요금이 그대로 나간다 (§17).
"""

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


def post(ip: str = "1.2.3.4"):
    return client.post("/api/v1/readings", json=BODY, headers={"X-Forwarded-For": ip})


def test_allows_up_to_the_limit():
    for i in range(rate_limit.PER_IP_LIMIT):
        assert post().status_code == 201, f"{i + 1}번째가 막혔다"


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
    assert post(ip="2.2.2.2").status_code == 201


def test_global_limit_protects_the_bill():
    """IP 를 바꿔가며 때려도 전체 한도에서 멈춘다."""
    for i in range(rate_limit.GLOBAL_LIMIT):
        post(ip=f"10.0.{i // 250}.{i % 250}")
    assert post(ip="9.9.9.9").status_code == 429


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


def test_forwarded_header_is_used():
    """터널 뒤에서는 실제 주소가 헤더로 온다."""

    class Req:
        headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
        client = None

    assert rate_limit.client_ip(Req()) == "203.0.113.7"  # type: ignore[arg-type]


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
