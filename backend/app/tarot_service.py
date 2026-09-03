"""타로 3장 스프레드 (PRD §8.6).

주제 수(1~5)와 무관하게 **항상 3장**이고, 세 장은 서로 겹치지 않는다(비복원 추출).
seed 를 저장하면 같은 링크가 항상 같은 카드를 낸다 — 재현성이 요구사항이다.

카드 의미는 여기 표에 두고 LLM 에는 이 키워드만 넘긴다.
LLM 이 카드 뜻을 지어내지 않게 하려는 것이다 (PRD §8.6).
"""

import random
from dataclasses import dataclass

# 스프레드 자리 (PRD §8.6)
SPREAD = (
    ("현재", "지금 놓인 자리"),
    ("조언", "지금 할 수 있는 것"),
    ("방향", "이대로 가면"),
)


@dataclass(frozen=True)
class Card:
    name: str
    name_ko: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class DrawnCard:
    position: str
    position_ko: str
    card: str
    card_ko: str
    reversed: bool
    keywords: list[str]


def _major(n: int, en: str, ko: str, *kw: str) -> Card:
    return Card(name=en, name_ko=ko, keywords=kw)


# ── 메이저 아르카나 22장 ──────────────────────────────────────
_MAJORS = [
    _major(0, "The Fool", "바보", "시작", "무모함", "가능성"),
    _major(1, "The Magician", "마법사", "의지", "실행력", "재능"),
    _major(2, "The High Priestess", "여교황", "직관", "비밀", "기다림"),
    _major(3, "The Empress", "여황제", "풍요", "돌봄", "결실"),
    _major(4, "The Emperor", "황제", "권위", "질서", "책임"),
    _major(5, "The Hierophant", "교황", "가르침", "관습", "조언자"),
    _major(6, "The Lovers", "연인", "선택", "이끌림", "조화"),
    _major(7, "The Chariot", "전차", "돌파", "추진", "승부"),
    _major(8, "Strength", "힘", "인내", "부드러운 힘", "다스림"),
    _major(9, "The Hermit", "은둔자", "성찰", "거리두기", "준비"),
    _major(10, "Wheel of Fortune", "운명의 수레바퀴", "전환점", "순환", "기회"),
    _major(11, "Justice", "정의", "균형", "판단", "책임"),
    _major(12, "The Hanged Man", "매달린 사람", "보류", "관점 전환", "감내"),
    _major(13, "Death", "죽음", "끝맺음", "정리", "새 국면"),
    _major(14, "Temperance", "절제", "조절", "중용", "회복"),
    _major(15, "The Devil", "악마", "집착", "굴레", "유혹"),
    _major(16, "The Tower", "탑", "급변", "붕괴", "각성"),
    _major(17, "The Star", "별", "희망", "회복", "치유"),
    _major(18, "The Moon", "달", "혼란", "오해", "불안"),
    _major(19, "The Sun", "태양", "성취", "활력", "명료"),
    _major(20, "Judgement", "심판", "결산", "부름", "재개"),
    _major(21, "The World", "세계", "완성", "통합", "마무리"),
]

# ── 마이너 아르카나 56장 ──────────────────────────────────────
# 수트별 성격 + 숫자별 단계로 키워드를 구성한다.
_SUITS = [
    ("Wands", "완드", "의욕"),
    ("Cups", "컵", "마음"),
    ("Swords", "소드", "생각"),
    ("Pentacles", "펜타클", "현실"),
]
_RANKS = [
    ("Ace", "에이스", "시작", "계기"),
    ("Two", "2", "균형", "짝"),
    ("Three", "3", "확장", "협력"),
    ("Four", "4", "안정", "정체"),
    ("Five", "5", "갈등", "상실"),
    ("Six", "6", "회복", "조력"),
    ("Seven", "7", "점검", "인내"),
    ("Eight", "8", "속도", "집중"),
    ("Nine", "9", "축적", "부담"),
    ("Ten", "10", "완결", "과잉"),
    ("Page", "페이지", "배움", "소식"),
    ("Knight", "나이트", "행동", "돌진"),
    ("Queen", "퀸", "품기", "성숙"),
    ("King", "킹", "다스림", "책임"),
]

# 수트(무엇에 관한 일인가) + 랭크(어느 단계인가) 두 축으로 키워드를 만든다.
# Q5(카드 이미지·상세 의미 확정)가 정해지면 이 표를 실제 해석 문안으로 교체한다.
_MINORS = [
    Card(
        name=f"{rank_en} of {suit_en}",
        name_ko=f"{suit_ko} {rank_ko}",
        keywords=(suit_kw, rank_kw1, rank_kw2),
    )
    for suit_en, suit_ko, suit_kw in _SUITS
    for rank_en, rank_ko, rank_kw1, rank_kw2 in _RANKS
]

DECK: list[Card] = _MAJORS + _MINORS
assert len(DECK) == 78, f"덱이 78장이 아니다: {len(DECK)}"


def draw(seed: int) -> list[DrawnCard]:
    """seed 로 3장을 뽑는다. 같은 seed 면 항상 같은 결과."""
    rng = random.Random(seed)
    picked = rng.sample(DECK, len(SPREAD))  # 비복원 추출
    return [
        DrawnCard(
            position=key,
            position_ko=label,
            card=card.name,
            card_ko=card.name_ko,
            reversed=rng.random() < 0.5,
            keywords=list(card.keywords),
        )
        for (key, label), card in zip(SPREAD, picked)
    ]


def new_seed() -> int:
    """리포트마다 새로 만들고 DB 에 저장한다 (PRD §9 readings.tarot_seed)."""
    return random.SystemRandom().randrange(2**62)
