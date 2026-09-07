"""손님이 직접 뽑는 부채꼴 78장 (PRD §8.6.1).

서버가 알아서 뽑아 주면 결과가 남의 점괘처럼 읽힌다.
78장을 뒷면으로 깔고 번호 3개를 고르게 한다.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.tarot_service import FAN_SIZE, SPREAD, draw_picks

client = TestClient(app)

BASE = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "solar",
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "birth_place": "서울",
    "topics": ["연애"],
}


def 직접뽑기(picks, mode="manual"):
    body = {**BASE, "tarot_mode": mode}
    if picks is not None:
        body["tarot_picks"] = picks
    return client.post("/api/v1/readings", json=body)


def test_고른_번호로_3장이_열린다():
    r = 직접뽑기([7, 42, 61])
    assert r.status_code == 201
    tarot = r.json()["tarot"]
    assert len(tarot) == len(SPREAD)
    assert [c["pick"] for c in tarot] == [7, 42, 61]


def test_고른_순서가_자리를_정한다():
    """첫 번째로 고른 번호가 ① 지금 놓인 자리다 (PRD §8.6.1)."""
    tarot = 직접뽑기([61, 7, 42]).json()["tarot"]
    assert [c["pick"] for c in tarot] == [61, 7, 42]
    assert [c["position_ko"] for c in tarot] == [label for _, label in SPREAD]


def test_화면에_보여줄_것이_다_온다():
    """자리 이름·고른 번호·카드·정역 네 가지가 있어야 화면을 그릴 수 있다."""
    for c in 직접뽑기([1, 2, 3]).json()["tarot"]:
        assert c["position_ko"]
        assert c["pick"] in (1, 2, 3)
        assert c["card_ko"]
        assert isinstance(c["reversed"], bool)


def test_같은_번호를_두_번_고를_수_없다():
    r = 직접뽑기([7, 7, 42])
    assert r.status_code == 400
    assert r.json()["error"]["field"] == "tarot_picks"


def test_번호는_1부터_78까지():
    for bad in ([0, 1, 2], [1, 2, FAN_SIZE + 1], [-3, 1, 2]):
        assert 직접뽑기(bad).status_code == 400, f"{bad} 가 통과했다"


def test_세_장이_아니면_막는다():
    for bad in ([7, 42], [7, 42, 61, 3], []):
        assert 직접뽑기(bad).status_code == 400, f"{bad} 가 통과했다"


def test_manual_인데_번호가_없으면_막는다():
    assert 직접뽑기(None).status_code == 400


def test_auto_에_번호를_보내면_막는다():
    """손님은 골랐다고 생각하는데 서버가 딴 카드를 뽑아 주는 것이 가장 나쁘다."""
    assert 직접뽑기([7, 42, 61], mode="auto").status_code == 400


def test_auto_는_그대로_돈다():
    """기존 흐름이 깨지지 않아야 한다 — API 기본값은 여전히 auto 다."""
    r = client.post("/api/v1/readings", json=BASE)      # tarot_mode 생략
    assert r.status_code == 201
    tarot = r.json()["tarot"]
    assert len(tarot) == len(SPREAD)
    assert all(c["pick"] is None for c in tarot)


def test_번호는_자리이지_카드가_아니다():
    """매 요청 새로 섞으므로 7번을 골라도 올 때마 다른 카드가 나온다.

    번호에 카드를 고정하면 손님이 외워서 결과를 고를 수 있게 되어
    뽑는 행위가 선택이 되어 버린다 (PRD §8.6.1).
    """
    나온카드 = {직접뽑기([7, 42, 61]).json()["tarot"][0]["card"] for _ in range(12)}
    assert len(나온카드) > 1, "7번이 늘 같은 카드다 — 섞이지 않았다"


def test_고른_3장만_돌려준다():
    """78장 매핑을 주면 다음에 무엇을 고르면 무엇이 나오는지 알게 된다."""
    body = 직접뽑기([7, 42, 61]).json()
    assert len(body["tarot"]) == 3
    assert "fan" not in body and "deck" not in body and "tarot_seed" not in body


def test_배치는_seed_로_재현된다():
    """같은 seed·같은 번호면 같은 카드 — 저장·복원에 필요하다."""
    a = draw_picks([7, 42, 61], seed=12345)
    b = draw_picks([7, 42, 61], seed=12345)
    assert [c.card for c in a] == [c.card for c in b]
    assert [c.card for c in a] != [c.card for c in draw_picks([7, 42, 61], seed=999)]


def test_문자열_번호는_받지_않는다():
    """계약이 느슨하면 프론트와 서버가 다른 것을 주고받아도 조용히 넘어간다.

    pydantic 기본값은 강제 변환이라 ["7","42","61"] 이 통과했다(점검에서 발견).
    값 검증은 그 뒤에도 정상이라 위험하지는 않았지만, 숫자로 약속한 자리다.
    """
    r = client.post(
        "/api/v1/readings",
        json={**BASE, "tarot_mode": "manual", "tarot_picks": ["7", "42", "61"]},
    )
    assert r.status_code == 400
    assert r.json()["error"]["field"] == "tarot_picks"
