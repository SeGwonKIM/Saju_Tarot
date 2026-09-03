"""달력 변환 엔드포인트 (PRD §10.1, §10.3).

주소는 명사, 동작은 메서드로 — `/calendar/convert` 는 변환이라는 동작 자체가
자원이 아니라서 예외적으로 동사를 쓴다(명세에 그렇게 확정돼 있다).
"""

from typing import Literal

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field, field_validator

from ..calendar_service import (
    MAX_YEAR,
    MIN_YEAR,
    lunar_to_solar,
    lunar_year_info,
    solar_to_lunar,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


class ConvertRequest(BaseModel):
    calendar_type: Literal["solar", "lunar"]
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["1988-03-05"])
    is_leap_month: bool = False

    @field_validator("date")
    @classmethod
    def parts_in_range(cls, v: str) -> str:
        _, month, day = (int(x) for x in v.split("-"))
        if not 1 <= month <= 12:
            raise ValueError("월은 1~12 사이여야 합니다.")
        if not 1 <= day <= 31:
            raise ValueError("일은 1~31 사이여야 합니다.")
        return v


class ConvertResponse(BaseModel):
    solar_date: str
    lunar_date: str
    is_leap_month: bool
    ganji: str


class LunarMonthOut(BaseModel):
    month: int
    days: int
    has_leap: bool
    leap_days: int | None


class LunarYearResponse(BaseModel):
    year: int
    months: list[LunarMonthOut]


@router.post("/convert", response_model=ConvertResponse)
def convert(body: ConvertRequest) -> ConvertResponse:
    year, month, day = (int(x) for x in body.date.split("-"))
    result = (
        solar_to_lunar(year, month, day)
        if body.calendar_type == "solar"
        else lunar_to_solar(year, month, day, body.is_leap_month)
    )
    return ConvertResponse(**result.__dict__)


@router.get("/lunar-year/{year}", response_model=LunarYearResponse)
def lunar_year(year: int = Path(ge=MIN_YEAR, le=MAX_YEAR)) -> LunarYearResponse:
    return LunarYearResponse(
        year=year,
        months=[LunarMonthOut(**m.__dict__) for m in lunar_year_info(year)],
    )
