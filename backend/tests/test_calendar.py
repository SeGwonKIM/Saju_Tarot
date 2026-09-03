"""음↔양 변환 테스트 (PRD §16.1).

골든 테스트의 씨앗이다. 4단계에서 KASI OpenAPI 대조로 100건까지 늘린다.
경계 케이스를 여기에 계속 쌓는다.
"""

import pytest
from fastapi.testclient import TestClient

from app.calendar_service import (
    CalendarError,
    has_leap_month,
    lunar_to_solar,
    lunar_year_info,
    solar_to_lunar,
)
from app.main import app

client = TestClient(app)


# ── 실제 윤달과 일치하는지 (왕복 검증의 핵심) ─────────────────
@pytest.mark.parametrize(
    "year,leap_month",
    [(1987, 6), (1990, 5), (1993, 3), (1995, 8), (1998, 5), (2020, 4), (2023, 2)],
)
def test_known_leap_months(year, leap_month):
    months = [m.month for m in lunar_year_info(year) if m.has_leap]
    assert months == [leap_month]


def test_1988_has_no_leap_month():
    """라이브러리는 없는 윤달에도 True 를 반환한다 — 왕복 검증이 이를 잡아야 한다."""
    assert [m.month for m in lunar_year_info(1988) if m.has_leap] == []
    assert has_leap_month(1988, 3) is False


def test_nonexistent_leap_month_rejected():
    with pytest.raises(CalendarError) as e:
        lunar_to_solar(1988, 3, 5, is_leap=True)
    assert e.value.code == "LUNAR_DATE_NOT_FOUND"
    assert "윤3월" in e.value.message


# ── 변환 정확도 ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "lunar,is_leap,solar",
    [
        (("1988-03-05"), False, "1988-04-20"),
        (("1990-05-01"), False, "1990-05-24"),
        (("1990-05-01"), True, "1990-06-23"),  # 윤5월
        (("2000-01-01"), False, "2000-02-05"),
    ],
)
def test_lunar_to_solar(lunar, is_leap, solar):
    y, m, d = (int(x) for x in lunar.split("-"))
    assert lunar_to_solar(y, m, d, is_leap).solar_date == solar


@pytest.mark.parametrize(
    "solar,lunar,is_leap",
    [
        ("1988-04-20", "1988-03-05", False),
        ("1990-06-23", "1990-05-01", True),
        ("1975-11-20", "1975-10-18", False),
        ("2026-09-03", "2026-07-22", False),
    ],
)
def test_solar_to_lunar(solar, lunar, is_leap):
    y, m, d = (int(x) for x in solar.split("-"))
    got = solar_to_lunar(y, m, d)
    assert (got.lunar_date, got.is_leap_month) == (lunar, is_leap)


def test_round_trip_across_years():
    """양 → 음 → 양 이 원래 날짜로 돌아와야 한다."""
    for solar in ["1900-01-15", "1950-06-30", "1988-02-29", "2000-02-29", "2026-01-01"]:
        y, m, d = (int(x) for x in solar.split("-"))
        lun = solar_to_lunar(y, m, d)
        ly, lm, ld = (int(x) for x in lun.lunar_date.split("-"))
        assert lunar_to_solar(ly, lm, ld, lun.is_leap_month).solar_date == solar


def test_lunar_month_days_are_29_or_30():
    for m in lunar_year_info(1990):
        assert m.days in (29, 30)
        if m.has_leap:
            assert m.leap_days in (29, 30)


# ── 범위·형식 ─────────────────────────────────────────────────
def test_year_out_of_range():
    with pytest.raises(CalendarError) as e:
        solar_to_lunar(1899, 1, 1)
    assert e.value.code == "YEAR_OUT_OF_RANGE"


def test_invalid_solar_date():
    with pytest.raises(CalendarError):
        solar_to_lunar(2000, 2, 30)


# ── API 계약 (PRD §10.1, §10.6) ───────────────────────────────
def test_convert_endpoint_lunar():
    r = client.post(
        "/api/v1/calendar/convert",
        json={"calendar_type": "lunar", "date": "1988-03-05", "is_leap_month": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["solar_date"] == "1988-04-20"
    assert body["lunar_date"] == "1988-03-05"
    assert body["is_leap_month"] is False
    assert body["ganji"]


def test_convert_endpoint_missing_leap_month_is_422():
    r = client.post(
        "/api/v1/calendar/convert",
        json={"calendar_type": "lunar", "date": "1988-03-05", "is_leap_month": True},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "LUNAR_DATE_NOT_FOUND"
    assert r.json()["error"]["field"] == "date"


def test_convert_endpoint_bad_format_is_400():
    """형식 오류는 400 — FastAPI 기본값(422)이 아니라 명세를 따른다."""
    r = client.post(
        "/api/v1/calendar/convert",
        json={"calendar_type": "lunar", "date": "1988/03/05"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"


def test_convert_endpoint_bad_month_is_400():
    r = client.post(
        "/api/v1/calendar/convert",
        json={"calendar_type": "solar", "date": "1988-13-05"},
    )
    assert r.status_code == 400


def test_lunar_year_endpoint():
    r = client.get("/api/v1/calendar/lunar-year/1990")
    assert r.status_code == 200
    body = r.json()
    assert body["year"] == 1990
    assert len(body["months"]) == 12
    leap = [m for m in body["months"] if m["has_leap"]]
    assert [m["month"] for m in leap] == [5]


def test_lunar_year_out_of_range_is_400():
    r = client.get("/api/v1/calendar/lunar-year/1800")
    assert r.status_code == 400
