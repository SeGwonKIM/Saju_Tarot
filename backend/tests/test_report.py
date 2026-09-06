"""문장 생성 레이어 테스트 (PRD §11).

네트워크를 타지 않는다. 실제 호출은 맨 아래 live 마커 테스트 하나뿐이고 기본 제외다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.report_service import (
    BANNED,
    TOPIC_RULES,
    TOPIC_WEIGHTS,
    NullReportGenerator,
    Report,
    _schema,
    _user_prompt,
    build_facts,
    has_banned_word,
)
from app.routers.readings import get_generator
from tests.conftest import FakeReportGenerator

client = TestClient(app)

VALID = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "lunar",
    "birth_date": "1988-03-05",
    "birth_time": "20:30",
    "birth_place": "서울",
    "topics": ["재회운", "상대방속마음", "연애"],
    "tarot_mode": "auto",
}

PILLARS = {
    "year": {"gan": "戊", "ji": "辰", "ko": "무진"},
    "month": {"gan": "丙", "ji": "辰", "ko": "병진"},
    "day": {"gan": "乙", "ji": "巳", "ko": "을사"},
    "hour": {"gan": "丙", "ji": "戌", "ko": "병술"},
}
TAROT = [
    {"position_ko": "지금 놓인 자리", "card_ko": "별", "reversed": False, "keywords": ["희망"]},
]


# ── 사실 블록 (계산 결과를 고정 사실로 넘긴다) ────────────────


def test_facts_include_all_pillars_and_elements():
    facts = build_facts(PILLARS, {"목": 1.6, "화": 4.2}, ["토 과다"], TAROT, "1988-04-20 20:30")
    assert "무진" in facts and "병술" in facts
    assert "토 과다" in facts
    assert "지금 놓인 자리 = 별(정방향" in facts
    assert "1988-04-20 20:30" in facts


def test_facts_note_unknown_hour():
    facts = build_facts({**PILLARS, "hour": None}, {"목": 1}, ["균형"], TAROT, "기준")
    assert "출생시각 미상" in facts
    assert "병술" not in facts


def test_facts_forbid_per_topic_cards():
    """3장을 주제별로 쪼개 배정하지 말라는 지시가 사실 블록에 들어간다 (PRD §8.6)."""
    facts = build_facts(PILLARS, {"목": 1}, ["균형"], TAROT, "기준")
    assert "주제마다 다른 카드를 배정하지 마십시오" in facts


# ── 출력 스키마 (프롬프트 부탁이 아니라 스키마로 막는다) ──────


def test_schema_pins_topics_with_enum():
    """실측: 모델이 요청하지 않은 '종합' 주제를 만들어 냈다. enum 으로 구조적으로 차단한다."""
    topics = ["재회운", "연애"]
    s = _schema(topics)
    advice = s["schema"]["properties"]["advice"]
    assert advice["items"]["properties"]["topic"]["enum"] == topics
    assert advice["minItems"] == advice["maxItems"] == 2
    assert s["strict"] is True


def test_schema_fixes_flow_at_three_lines():
    flow = _schema(["연애"])["schema"]["properties"]["monthly_flow"]
    assert flow["minItems"] == flow["maxItems"] == 3


def test_schema_rejects_extra_fields():
    s = _schema(["연애"])["schema"]
    assert s["additionalProperties"] is False


# ── 프롬프트 (주제별 비중과 주의사항, 인젝션 대비) ────────────


def test_prompt_includes_weights_and_rules():
    p = _user_prompt("사실", "홍길동", ["재회운", "상대방속마음"])
    assert "사주 3 : 타로 7" in p  # 재회운
    assert "사주 1 : 타로 9" in p  # 상대방속마음
    assert TOPIC_RULES["재회운"] in p
    assert "상대의 생년월일이 없다는 사실" in p


def test_prompt_wraps_user_data():
    """이름은 지시가 아니라 값으로 감싼다 (PRD §12.18)."""
    p = _user_prompt("사실", "홍길동", ["연애"])
    assert "<사용자데이터>" in p and "</사용자데이터>" in p
    assert p.index("<사용자데이터>") < p.index("홍길동") < p.index("</사용자데이터>")


def test_every_topic_has_weight_and_rule():
    from app.routers.readings import TOPICS

    for t in TOPICS:
        assert t in TOPIC_WEIGHTS
        assert t in TOPIC_RULES


# ── 금지어 후처리 ─────────────────────────────────────────────


@pytest.mark.parametrize("word", ["암", "완치", "수익 보장", "사망"])
def test_banned_word_detected(word):
    r = Report(
        saju_reading=["첫 줄.", "둘째 줄.", "셋째 줄."],
        monthly_flow=[f"이번 달은 {word} 관련 흐름입니다."],
        advice={},
        keywords=[],
    )
    assert has_banned_word(r) == word


def test_clean_report_passes():
    r = Report(
        saju_reading=["부드럽게 뻗는 결입니다.", "성실이 강점입니다.", "속도는 느린 편입니다."],
        monthly_flow=["차분히 흐름을 살피기 좋은 달입니다."],
        advice={"연애": "상대의 속도를 확인해 보시면 좋습니다."},
        keywords=["정리"],
    )
    assert has_banned_word(r) is None


def test_banned_list_covers_medical_and_investment():
    assert any(w in BANNED for w in ("암", "완치"))
    assert "수익 보장" in BANNED


# ── 부분 성공 경로 (PRD §11.3) ────────────────────────────────


def test_null_generator_returns_none():
    assert NullReportGenerator().generate("사실", "홍길동", ["연애"]) is None


def test_endpoint_returns_report_when_generation_succeeds(no_network_generator):
    """계산 → 풀이 두 단계로 받는다 (v3.0)."""
    first = client.post("/api/v1/readings", json=VALID)
    assert first.status_code == 201
    assert first.json()["report"] is None, "계산 단계에서는 풀이가 없다"

    r = client.post(f"/api/v1/readings/{first.json()['id']}/report")
    assert r.status_code == 200
    d = r.json()
    assert len(d["report"]["monthly_flow"]) == 3
    assert set(d["report"]["advice"]) == set(VALID["topics"])
    assert d["report"]["disclaimer"]
    assert d["report_model"] == "fake-model"


def test_report_is_not_regenerated(no_network_generator):
    """이미 만든 풀이는 다시 만들지 않는다 — 새로고침해도 요금이 두 번 안 나간다."""
    rid = client.post("/api/v1/readings", json=VALID).json()["id"]
    first = client.post(f"/api/v1/readings/{rid}/report").json()
    again = client.post(f"/api/v1/readings/{rid}/report").json()
    assert again["report"] == first["report"]


def test_same_person_reuses_only_the_saju_reading(no_network_generator):
    """**사주 풀이만** 고정된다 (v3.3).

    원국은 평생 값이라 같은 사람이면 언제 봐도 같은 말이 나와야 한다.
    반대로 이번 달 흐름·주제별 조언은 그때 뽑은 카드를 근거로 쓰므로
    다시 만들어야 한다 — 카드는 매번 새로 뽑히는데(v3.3) 조언을 재사용하면
    **화면에 없는 카드를 두고 쓴 조언**이 된다. 조언은 타로 비중이 크다
    (상대방속마음 1:9, 재회운 3:7).
    """
    body = {**VALID, "name": "풀이고정시험"}
    a = client.post("/api/v1/readings", json=body).json()["id"]
    first = client.post(f"/api/v1/readings/{a}/report").json()["report"]

    b = client.post("/api/v1/readings", json=body).json()["id"]
    second = client.post(f"/api/v1/readings/{b}/report").json()["report"]

    assert a != b, "주소는 매번 새로 만든다"
    assert second["saju_reading"] == first["saju_reading"], "사주 풀이는 고정이어야 한다"


def test_same_birth_different_name_gets_a_new_report(no_network_generator):
    """생년월일이 같아도 **이름이 다르면 새로 쓴다** (v3.2 · 사용자 요청)."""
    a = client.post("/api/v1/readings", json={**VALID, "name": "이름가"}).json()["id"]
    client.post(f"/api/v1/readings/{a}/report")
    calls = len(no_network_generator.calls)

    b = client.post("/api/v1/readings", json={**VALID, "name": "이름나"}).json()["id"]
    client.post(f"/api/v1/readings/{b}/report")
    assert len(no_network_generator.calls) == calls + 1, "이름이 다르면 새로 만들어야 한다"


def test_report_on_missing_reading_is_404(no_network_generator):
    assert client.post("/api/v1/readings/r-nope/report").status_code == 404


def test_endpoint_survives_generation_failure():
    """문장 생성이 실패해도 계산 결과는 그대로 나가고 500 이 아니다."""
    app.dependency_overrides[get_generator] = lambda: FakeReportGenerator(fail=True)
    try:
        # 이름을 달리해 재사용을 피한다 — 같은 이름이면 앞서 만든 풀이를
        # 그대로 쓰므로(v3.2), 생성 실패 경로를 시험할 수 없다.
        rid = client.post(
            "/api/v1/readings", json={**VALID, "name": "생성실패시험"}
        ).json()["id"]
        r = client.post(f"/api/v1/readings/{rid}/report")
        assert r.status_code == 200
        d = r.json()
        assert d["report"] is None
        assert d["report_model"] is None
        assert d["pillars"]["year"]["ko"]  # 계산 결과는 살아 있다
        assert len(d["tarot"]) == 3
    finally:
        app.dependency_overrides.pop(get_generator, None)


def test_generator_receives_only_selected_topics(no_network_generator):
    """주제와 이름이 두 단계를 건너서도 그대로 전달되어야 한다 (v3.0).

    이름은 암호화되어 저장되므로, 풀이 단계에서 복호화해 넘긴다.
    주제는 계산 단계에서 payload 에 저장해 두지 않으면 여기서 알 수 없다.
    """
    rid = client.post(
        "/api/v1/readings", json={**VALID, "topics": ["재물"], "name": "주제전달시험"}
    ).json()["id"]
    client.post(f"/api/v1/readings/{rid}/report")
    _, name, topics = no_network_generator.calls[-1]
    assert topics == ["재물"]
    assert name == "주제전달시험", "암호화된 이름을 복호화해 넘겨야 한다"


# ── 실제 호출 (기본 제외, `pytest -m live` 로만 실행) ─────────


@pytest.mark.live
def test_live_generation_produces_korean_sentences():
    from app.config import get_settings
    from app.report_service import OpenAIReportGenerator

    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "CHANGE_ME":
        pytest.skip("OPENAI_API_KEY 없음")

    gen = OpenAIReportGenerator(settings.openai_api_key, settings.report_model)
    facts = build_facts(PILLARS, {"목": 1.6, "화": 4.2, "토": 7.2, "금": 0.6, "수": 0.4},
                        ["토 과다"], TAROT, "1988-04-20 20:30")
    report = gen.generate(facts, "홍길동", ["재회운", "연애"])

    assert report is not None
    assert len(report.monthly_flow) == 3
    assert set(report.advice) == {"재회운", "연애"}      # enum 이 주제를 고정했는지
    assert has_banned_word(report) is None
    assert all(len(s) <= 120 for s in report.monthly_flow)


def test_banned_word_detected_in_saju_reading():
    """사주 풀이도 금지어 검사를 받는다 — 성격 얘기라고 예외가 아니다."""
    r = Report(
        saju_reading=["암을 조심해야 하는 사주입니다.", "둘째.", "셋째."],
        monthly_flow=["평범한 문장입니다."],
        advice={},
        keywords=[],
    )
    assert has_banned_word(r) == "암"


def test_schema_requires_saju_reading():
    """사주 풀이는 **5항목 고정**이다 (v2.27).

    한 줄짜리 3개로는 상담글이 되지 않아 항목을 늘렸다. 개수를 스키마로 못 박아
    모델이 마음대로 줄이지 못하게 한다 — 프롬프트로 부탁하면 지키지 않는다.
    """
    s = _schema(["연애"])["schema"]
    assert "saju_reading" in s["required"]
    block = s["properties"]["saju_reading"]
    assert block["minItems"] == block["maxItems"] == 5

    # 이번 달 흐름은 3항목 그대로다 ("이번 달 흐름 세 줄"이 서비스 설명이다)
    flow = s["properties"]["monthly_flow"]
    assert flow["minItems"] == flow["maxItems"] == 3


def test_facts_include_interpretation():
    facts = build_facts(
        PILLARS, {"목": 1}, ["균형"], TAROT, "기준",
        interpretation=["일간은 을목(乙) — 음의 목.", "십성 중 정재가 가장 많다."],
    )
    assert "풀이 재료" in facts
    assert "을목" in facts and "정재" in facts
