"""출생지 목록 검증 (PRD §6.1 필드 7, §5.4 계약 단일 출처).

서버가 화이트리스트로 검증하므로, 프론트 목록과 **이름이 하나라도 다르면**
그 지역을 고른 손님이 400 을 맞는다. 그래서 두 파일을 실제로 대조한다.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.readings import BIRTH_PLACES

client = TestClient(app)

FRONTEND_SCHEMA = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "schemas" / "reading.ts"
)

BASE = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "solar",
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "topics": ["연애"],
    "tarot_mode": "auto",
}


def _frontend_places() -> dict[str, float]:
    """프론트 BIRTH_PLACES 배열을 읽어 온다."""
    src = FRONTEND_SCHEMA.read_text(encoding="utf-8")
    block = src[src.index("export const BIRTH_PLACES") : src.index("/** 표준자오선")]
    return {
        m.group(1): float(m.group(2))
        for m in re.finditer(r"name:\s*'([^']+)',\s*longitude:\s*([\d.]+)", block)
    }


def test_frontend_and_backend_lists_match():
    front = _frontend_places()
    assert front, "프론트에서 BIRTH_PLACES 를 읽지 못했습니다"
    assert set(front) == set(BIRTH_PLACES), (
        f"프론트에만: {set(front) - set(BIRTH_PLACES)} / "
        f"서버에만: {set(BIRTH_PLACES) - set(front)}"
    )
    for name, lon in front.items():
        assert abs(lon - BIRTH_PLACES[name]) < 0.001, f"{name} 경도 불일치"


def test_covers_all_17_regions():
    """17개 시·도 + 해외 = 18개."""
    assert len(BIRTH_PLACES) == 18
    for must in ("서울", "세종", "제주", "경기(수원)", "전남(무안)", "경북(안동)", "해외·모름"):
        assert must in BIRTH_PLACES


def test_longitudes_are_in_korea_range():
    """해외·모름(표준자오선)을 뺀 나머지는 한반도 경도 범위 안에 있어야 한다."""
    for name, lon in BIRTH_PLACES.items():
        if name == "해외·모름":
            assert lon == 135.0
        else:
            assert 125.0 < lon < 132.0, f"{name} 경도가 범위 밖: {lon}"


@pytest.mark.parametrize("place", list(BIRTH_PLACES))
def test_every_place_is_accepted(place):
    """목록에 있는 지역은 전부 실제로 통과해야 한다."""
    r = client.post("/api/v1/readings", json={**BASE, "birth_place": place})
    assert r.status_code == 201, (place, r.status_code)


def test_unknown_place_is_rejected():
    r = client.post("/api/v1/readings", json={**BASE, "birth_place": "평양"})
    assert r.status_code == 400


def test_correction_differs_by_region():
    """서쪽일수록 진태양시가 늦다 — 보정값이 실제로 달라야 의미가 있다."""
    west = client.post("/api/v1/readings", json={**BASE, "birth_place": "전남(무안)"}).json()
    east = client.post("/api/v1/readings", json={**BASE, "birth_place": "울산"}).json()
    w = west["input_echo"]["true_solar_correction_min"]
    e = east["input_echo"]["true_solar_correction_min"]
    assert w < e, f"무안 {w}분, 울산 {e}분 — 서쪽이 더 늦어야 한다"
    assert e - w >= 10  # 두 끝 지역은 10분 이상 벌어진다
