"""이번 달 기운과 카드 재현성 (PRD §8.5, §8.6).

같은 사람이 같은 달에 다시 조회하면 **항상 같은 카드**여야 한다.
매번 달라지면 상담 리포트로서 신뢰가 서지 않고 "이번 달 흐름"이라는 말과도 안 맞는다.
"""

from datetime import datetime

from fastapi.testclient import TestClient

from app.korea_time import correct
from app.main import app
from app.saju_service import current_period
from app.tarot_service import draw, period_seed

client = TestClient(app)
SEOUL = 126.978

BODY = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "lunar",
    "birth_date": "1988-03-05",
    "birth_time": "20:30",
    "birth_place": "서울",
    "topics": ["재회운"],
    "tarot_mode": "auto",
}


def cards_of(payload: dict) -> list[tuple[str, bool]]:
    d = client.post("/api/v1/readings", json=payload).json()
    return [(c["card"], c["reversed"]) for c in d["tarot"]]


# ── 재현성 ────────────────────────────────────────────────────


def test_same_person_same_month_gets_same_cards():
    """새로고침할 때마다 카드가 달라지면 안 된다."""
    first = client.post("/api/v1/readings", json=BODY).json()
    second = client.post("/api/v1/readings", json=BODY).json()
    assert first["tarot"] == second["tarot"]
    assert first["tarot_seed"] == second["tarot_seed"]
    assert first["id"] == second["id"]


def test_different_person_gets_different_cards():
    a = cards_of(BODY)
    b = cards_of({**BODY, "birth_date": "1990-05-05"})
    assert a != b


def test_birth_time_changes_cards():
    a = cards_of(BODY)
    b = cards_of({**BODY, "birth_time": "03:10"})
    assert a != b


def test_topics_do_not_change_cards():
    """타로는 주제와 무관하게 3장 고정이다 (PRD §8.6)."""
    a = cards_of({**BODY, "topics": ["재회운"]})
    b = cards_of({**BODY, "topics": ["재회운", "재물", "대인관계"]})
    assert a == b


def test_month_change_changes_cards():
    """달(월운)이 바뀌면 카드도 바뀐다 — 이것이 '매달 바뀐다'의 의미다."""
    birth = "1988-04-20|20:30|서울"
    seeds = {
        period_seed(birth, f"병오|{m}월") for m in ("병신", "정유", "무술", "기해")
    }
    assert len(seeds) == 4  # 달마다 다른 seed

    cards = {tuple(c.card for c in draw(s)) for s in seeds}
    assert len(cards) == 4  # 카드도 달마다 다르다


def test_seed_is_deterministic_across_processes():
    """해시 기반이라 서버를 재시작해도 같은 값이 나온다 (random 은 그렇지 않다)."""
    a = period_seed("1988-04-20|20:30|서울", "병오|병신")
    b = period_seed("1988-04-20|20:30|서울", "병오|병신")
    assert a == b
    assert a != period_seed("1988-04-20|20:30|부산", "병오|병신")


# ── 이번 달 기운 ──────────────────────────────────────────────


def test_period_is_returned():
    d = client.post("/api/v1/readings", json=BODY).json()
    p = d["period"]
    assert p["year_ko"] and p["month_ko"]
    assert "년" in p["label"] and "월" in p["label"]


def test_period_uses_solar_terms_not_calendar_month():
    """월운은 절기로 바뀐다 — 달력 1일이 아니다 (PRD §8.2)."""
    def month_of(d: datetime) -> str:
        return current_period(d, correct(d, SEOUL).jieqi_reference).month.ko

    # 2024년 경칩은 3월 5일. 그 전후로 월운이 갈려야 한다
    assert month_of(datetime(2024, 3, 4, 12)) != month_of(datetime(2024, 3, 6, 12))
    # 달력이 바뀌는 3월 1일에는 월운이 그대로다
    assert month_of(datetime(2024, 2, 28, 12)) == month_of(datetime(2024, 3, 1, 12))


def test_period_changes_over_a_year():
    """1년이면 월운이 12번 바뀐다."""
    months = {
        current_period(d, correct(d, SEOUL).jieqi_reference).month.ko
        for d in (datetime(2024, m, 20, 12) for m in range(1, 13))
    }
    assert len(months) == 12
