"""만세력 검증 (PRD §16.1).

두 층으로 본다.
  ① 보정 레이어 — 우리가 짠 부분. 값을 직접 확인한다.
  ② 불변식 — 라이브러리 결과가 사주 규칙을 지키는지. 외부 데이터 없이 돈다.
     (KASI 절기 전수 대조는 tools/verify_solar_terms.py — 키가 필요해 별도)
"""

from datetime import datetime, timedelta

import pytest

from app.korea_time import correct, is_dst, standard_meridian
from app.saju_service import ELEMENTS, build_chart, solar_term_table

SEOUL = 126.978
BUSAN = 129.075

# ── ① 보정 레이어 ─────────────────────────────────────────────


def test_seoul_correction_is_minus_32_minutes():
    """서울은 표준자오선 135°보다 서쪽이라 진태양시가 약 32분 늦다 (PRD §8.2.1)."""
    c = correct(datetime(1988, 4, 20, 20, 30), SEOUL)
    assert c.true_solar_correction_min == -32
    assert c.standard_meridian == 135.0
    assert c.dst_applied is False


def test_correction_scales_with_longitude():
    """동쪽일수록 보정이 작다 — 부산은 서울보다 진태양시가 이르다."""
    seoul = correct(datetime(2000, 1, 1, 12, 0), SEOUL)
    busan = correct(datetime(2000, 1, 1, 12, 0), BUSAN)
    assert busan.true_solar > seoul.true_solar
    assert busan.true_solar_correction_min > seoul.true_solar_correction_min


def test_dst_subtracts_one_hour():
    """서머타임 구간 출생은 시계가 1시간 앞당겨져 있었다."""
    normal = correct(datetime(1988, 4, 20, 20, 30), SEOUL)
    dst = correct(datetime(1988, 6, 1, 20, 30), SEOUL)
    assert dst.dst_applied is True
    assert dst.true_solar_correction_min == normal.true_solar_correction_min - 60


@pytest.mark.parametrize(
    "d,expected",
    [
        (datetime(1988, 5, 7), False),   # 1988 서머타임 시작 전날
        (datetime(1988, 5, 8), True),    # 시작일
        (datetime(1988, 10, 8), True),   # 종료일
        (datetime(1988, 10, 9), False),  # 종료 다음날
        (datetime(1987, 5, 10), True),
        (datetime(1989, 6, 1), False),   # 1989년엔 없었다
    ],
)
def test_dst_boundaries(d, expected):
    """날짜 경계가 하루 틀리면 그 날 태어난 사람의 시주가 전부 틀린다."""
    assert is_dst(d.date()) is expected


@pytest.mark.parametrize(
    "d,meridian",
    [
        (datetime(1910, 1, 1), 127.5),
        (datetime(1912, 1, 1), 135.0),
        (datetime(1954, 3, 20), 135.0),
        (datetime(1954, 3, 21), 127.5),
        (datetime(1961, 8, 9), 127.5),
        (datetime(1961, 8, 10), 135.0),
        (datetime(2026, 1, 1), 135.0),
    ],
)
def test_standard_meridian_eras(d, meridian):
    assert standard_meridian(d.date()) == meridian


# ── ② 불변식 ──────────────────────────────────────────────────


def _chart_at(d: datetime, longitude: float = SEOUL):
    c = correct(d, longitude)
    return build_chart(c.jieqi_reference, c.true_solar)


def test_year_pillar_changes_exactly_once_per_year():
    """연주는 입춘에서만 바뀐다. 1월 1일이 아니다 (PRD §8.2)."""
    changes = []
    prev = None
    d = datetime(2024, 1, 1, 12, 0)
    while d < datetime(2025, 1, 1, 12, 0):
        cur = _chart_at(d).year.ko
        if prev and cur != prev:
            changes.append(d.date())
        prev = cur
        d += timedelta(days=1)
    assert len(changes) == 1
    # 입춘은 2월 3~5일 사이에 든다
    assert changes[0].month == 2 and 3 <= changes[0].day <= 5


def test_month_pillar_changes_twelve_times_per_year():
    """월주는 12절기 경계에서만 바뀐다 — 한 해에 정확히 12번."""
    changes = 0
    prev = None
    d = datetime(2024, 2, 5, 12, 0)  # 입춘 직후부터 한 해
    while d < datetime(2025, 2, 5, 12, 0):
        cur = _chart_at(d).month.ko
        if prev and cur != prev:
            changes += 1
        prev = cur
        d += timedelta(days=1)
    assert changes == 12


def test_day_pillar_cycles_through_60():
    """일주는 60갑자를 빠짐없이 순환한다."""
    seen = []
    d = datetime(2024, 1, 1, 12, 0)
    for _ in range(60):
        seen.append(_chart_at(d).day.ko)
        d += timedelta(days=1)
    assert len(set(seen)) == 60


def test_hour_pillar_changes_every_two_hours():
    """시주는 12지시(2시간)마다 바뀐다 — 하루에 서로 다른 시주가 12개."""
    kos = {
        _chart_at(datetime(2024, 6, 1, h, 0)).hour.ko  # type: ignore[union-attr]
        for h in range(24)
    }
    assert len(kos) == 12


def test_solar_terms_are_14_to_16_days_apart():
    """절기 간격은 약 15일 — 계산이 깨지면 여기서 드러난다."""
    table = solar_term_table(2024)
    times = sorted(datetime.fromisoformat(v) for v in table.values())
    gaps = [(b - a).days for a, b in zip(times, times[1:])]
    assert all(13 <= g <= 17 for g in gaps), gaps


def test_solar_term_table_is_korea_time():
    """라이브러리는 베이징 기준이므로 1시간을 더해 한국 기준으로 내놓는다."""
    table = solar_term_table(2024)
    ipchun = next(v for k, v in table.items() if k == "立春")
    assert ipchun.startswith("2024-02-04 17:")


# ── 시간 미상 (PRD §8.3) ──────────────────────────────────────


def test_unknown_time_omits_hour_pillar():
    c = correct(datetime(1975, 11, 20, 12, 0), SEOUL)
    chart = build_chart(c.jieqi_reference, None)
    assert chart.hour is None
    assert chart.year.ko and chart.month.ko and chart.day.ko


# ── 야자시 유파 (PRD §18.1 Q6) ────────────────────────────────


def test_midnight_rule_changes_day_pillar():
    """자시 출생은 유파에 따라 일주가 달라진다. 어떤 기준을 썼는지 밝혀야 한다."""
    c = correct(datetime(1988, 4, 20, 23, 50), SEOUL)  # 진태양시 23:18 → 자시
    early = build_chart(c.jieqi_reference, c.true_solar, midnight_rule="조자시")
    late = build_chart(c.jieqi_reference, c.true_solar, midnight_rule="야자시")
    assert early.day.ko != late.day.ko
    assert early.midnight_rule == "조자시"


def test_true_solar_shift_moves_hour_pillar_boundary():
    """보정이 시주 경계를 실제로 옮긴다 — 서울은 32분 늦으므로 시계 23:30은 아직 해시다.

    이 32분 구간에 태어난 사람은 시계만 보면 자시로 착각하기 쉽다.
    보정을 빼먹으면 시주가 통째로 틀린다.
    """
    before = correct(datetime(1988, 4, 20, 23, 30), SEOUL)
    after = correct(datetime(1988, 4, 20, 23, 50), SEOUL)
    assert before.true_solar.hour == 22  # 해시
    assert after.true_solar.hour == 23  # 자시

    # 해시 구간에서는 유파를 바꿔도 일주가 같다 (자시가 아니므로)
    a = build_chart(before.jieqi_reference, before.true_solar, midnight_rule="조자시")
    b = build_chart(before.jieqi_reference, before.true_solar, midnight_rule="야자시")
    assert a.day.ko == b.day.ko


# ── 오행 집계 (PRD §8.4) ──────────────────────────────────────


def test_elements_sum_and_verdict():
    chart = _chart_at(datetime(1988, 4, 20, 20, 30))
    assert set(chart.elements.counts) == set(ELEMENTS)
    assert sum(chart.elements.counts.values()) > 0
    assert chart.elements.verdict


def test_hidden_stems_can_be_disabled():
    """지장간을 빼면 오행 0인 칸이 늘어난다 (PRD §18.1 Q4 결정 근거)."""
    c = correct(datetime(1988, 4, 20, 20, 30), SEOUL)
    with_hidden = build_chart(c.jieqi_reference, c.true_solar, include_hidden_stems=True)
    without = build_chart(c.jieqi_reference, c.true_solar, include_hidden_stems=False)
    zeros_with = sum(1 for v in with_hidden.elements.counts.values() if v == 0)
    zeros_without = sum(1 for v in without.elements.counts.values() if v == 0)
    assert zeros_without >= zeros_with
    assert sum(without.elements.counts.values()) == 8  # 천간4 + 지지4


def test_engine_version_recorded():
    """재현성 — 어떤 엔진으로 계산했는지 리포트에 남는다 (PRD §17)."""
    chart = _chart_at(datetime(2000, 1, 1, 12, 0))
    assert "lunar-python" in chart.engine_version
