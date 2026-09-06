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


def test_same_person_gets_a_different_address_each_time():
    """카드는 같아도 **주소는 매번 새로 만든다** (v3.1 보안 수정).

    예전에는 주소가 카드 seed(생년월일의 해시)와 같았다. 그래서
      · 생년월일시·출생지가 같은 두 사람이 같은 주소를 받아,
        뒤 사람이 앞 사람 기록을 덮어썼다 (INSERT OR REPLACE)
      · 생년월일을 아는 사람이 주소를 계산해 남의 리포트를 열 수 있었다
    카드의 재현성과 주소의 비밀성은 별개다. 이 테스트가 그 분리를 지킨다.
    """
    a = client.post("/api/v1/readings", json=BODY).json()
    b = client.post("/api/v1/readings", json=BODY).json()
    assert a["id"] != b["id"], "같은 입력이 같은 주소를 내면 남의 기록을 덮어쓴다"
    assert len(a["id"]) >= 24, "주소가 짧으면 찍어서 맞힐 수 있다"


def test_response_does_not_leak_the_tarot_seed():
    """seed 는 생년월일의 해시다. 밖으로 내면 역산된다 (v3.1 보안 수정).

    공유 링크가 생년월일시를 지워도 이 값 하나로 되돌릴 수 있었다 —
    16년치를 10분 단위로 훑어 1.6초 만에 복원되는 것을 실측했다.
    """
    d = client.post("/api/v1/readings", json=BODY).json()
    assert "tarot_seed" not in d


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
