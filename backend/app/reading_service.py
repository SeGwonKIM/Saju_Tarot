"""사주 풀이 — 원국이 무엇을 뜻하는지 (PRD §8.7).

지금까지는 원국 네 기둥과 오행 숫자만 보여줬다. 손님 입장에서는
"무진 병진 을사 병술"과 "토 7.2"가 무슨 말인지 알 수 없다.
그 사이를 메우는 것이 이 모듈이다.

여기서 만드는 것은 **사실**이다. 해석 문장은 LLM 이 이 사실을 받아 쓴다.
  · 일간(日干) — 사주에서 '나'에 해당하는 글자
  · 십성(十星) — 일간에서 본 다른 글자들의 관계
  · 오행 균형 — 무엇이 넘치고 무엇이 모자란지

⚠️ 신강·신약 판정은 넣지 않았다. 득령·득지·득세를 어떻게 볼지 유파마다 달라
   한쪽을 임의로 고르면 그 자체가 오답이 된다 (PRD §18.2 Q16).
"""

from __future__ import annotations

from dataclasses import dataclass

# ── 일간 10천간 ───────────────────────────────────────────────
# 오행·음양과 함께, 그 일간을 부르는 전통적인 비유를 둔다.
# 비유는 해석의 출발점일 뿐이고, 실제 문장은 LLM 이 원국 전체를 보고 쓴다.
DAY_MASTERS: dict[str, dict[str, str]] = {
    "甲": {"ko": "갑목", "element": "목", "yin_yang": "양", "image": "곧게 자라는 큰 나무"},
    "乙": {"ko": "을목", "element": "목", "yin_yang": "음", "image": "휘어지며 뻗는 풀과 덩굴"},
    "丙": {"ko": "병화", "element": "화", "yin_yang": "양", "image": "만물을 비추는 태양"},
    "丁": {"ko": "정화", "element": "화", "yin_yang": "음", "image": "어둠을 밝히는 등불"},
    "戊": {"ko": "무토", "element": "토", "yin_yang": "양", "image": "넓고 단단한 큰 땅"},
    "己": {"ko": "기토", "element": "토", "yin_yang": "음", "image": "씨앗을 품는 기름진 흙"},
    "庚": {"ko": "경금", "element": "금", "yin_yang": "양", "image": "다듬지 않은 무쇠와 바위"},
    "辛": {"ko": "신금", "element": "금", "yin_yang": "음", "image": "세공을 마친 보석"},
    "壬": {"ko": "임수", "element": "수", "yin_yang": "양", "image": "쉼 없이 흐르는 큰 물"},
    "癸": {"ko": "계수", "element": "수", "yin_yang": "음", "image": "만물을 적시는 이슬비"},
}

# 라이브러리는 간체자로 준다. 한글로 옮긴다.
SHISHEN_KO: dict[str, str] = {
    "比肩": "비견", "劫财": "겁재",
    "食神": "식신", "伤官": "상관",
    "偏财": "편재", "正财": "정재",
    "七杀": "편관", "正官": "정관",
    "偏印": "편인", "正印": "정인",
}

# 십성이 삶에서 무엇을 가리키는지 — LLM 에 넘길 사실
SHISHEN_MEANING: dict[str, str] = {
    "비견": "자립·동료·경쟁",
    "겁재": "추진·나눔·다툼",
    "식신": "표현·여유·먹을 복",
    "상관": "재능·말솜씨·규칙 깨기",
    "편재": "큰 흐름의 돈·사교",
    "정재": "꾸준한 돈·성실",
    "편관": "압박·결단·위기 돌파",
    "정관": "책임·규범·자리",
    "편인": "직관·비주류 공부",
    "정인": "배움·보호·인복",
}


@dataclass(frozen=True)
class DayMaster:
    gan: str
    ko: str
    element: str
    yin_yang: str
    image: str


@dataclass(frozen=True)
class Interpretation:
    day_master: DayMaster
    """일간 — 사주에서 '나'"""
    shishen: dict[str, int]
    """십성별 개수 (천간 + 지장간)"""
    dominant: list[str]
    """가장 많이 나온 십성 (동점이면 여럿)"""
    summary_facts: list[str]
    """LLM 에 넘길 사실 문장들. 해석이 아니라 관측값이다"""


def _shishen_of(ec) -> dict[str, int]:
    counts: dict[str, int] = {}
    getters = [
        ec.getYearShiShenGan, ec.getMonthShiShenGan, ec.getTimeShiShenGan,
    ]
    for g in getters:
        ko = SHISHEN_KO.get(g())
        if ko:
            counts[ko] = counts.get(ko, 0) + 1

    # 지지는 지장간마다 십성이 나오므로 목록으로 온다
    for g in (
        ec.getYearShiShenZhi, ec.getMonthShiShenZhi,
        ec.getDayShiShenZhi, ec.getTimeShiShenZhi,
    ):
        for item in g():
            ko = SHISHEN_KO.get(item)
            if ko:
                counts[ko] = counts.get(ko, 0) + 1
    return counts


def interpret(
    jieqi_reference, true_solar, *, midnight_rule: str = "조자시"
) -> Interpretation:
    """원국에서 풀이의 재료를 뽑는다. 시간 미상이면 시주 몫은 빠진다."""
    from .saju_service import _eight_char  # 순환 참조를 피해 늦게 가져온다

    moment = true_solar if true_solar is not None else jieqi_reference
    ec = _eight_char(moment, midnight_rule)  # type: ignore[arg-type]

    gan = ec.getDayGan()
    meta = DAY_MASTERS[gan]
    dm = DayMaster(
        gan=gan,
        ko=meta["ko"],
        element=meta["element"],
        yin_yang=meta["yin_yang"],
        image=meta["image"],
    )

    counts = _shishen_of(ec)
    top = max(counts.values(), default=0)
    dominant = sorted(k for k, v in counts.items() if v == top and top > 0)

    facts = [
        f"일간은 {dm.ko}({dm.gan}) — {dm.yin_yang}의 {dm.element}, {dm.image}에 비유한다.",
    ]
    if dominant:
        joined = " · ".join(f"{d}({SHISHEN_MEANING[d]})" for d in dominant)
        facts.append(f"십성 중 가장 많이 드러난 것은 {joined}.")
    absent = [k for k in SHISHEN_MEANING if k not in counts]
    if absent:
        facts.append(f"원국에 드러나지 않은 십성: {' · '.join(absent)}.")

    return Interpretation(
        day_master=dm, shishen=counts, dominant=dominant, summary_facts=facts
    )
