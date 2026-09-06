"""리포트 생성 (PRD §10.2).

계산(원국·오행·타로)과 문장 생성(§11)을 이어 붙인다.
문장 생성이 실패하거나 키가 없으면 `report` 를 null 로 내보내고 계산 결과만 보여준다
— 500 을 내지 않는다 (부분 성공, PRD §11.3).

입력 검증은 프론트와 **같은 규칙을 여기서 다시** 한다 (PRD §12.2 프론트는 못 믿는다).
"""

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam
from pydantic import BaseModel, Field, field_validator

from ..calendar_service import CalendarError, lunar_to_solar
from ..config import get_settings
from ..korea_time import correct
from ..admin_auth import require_admin
from ..reading_service import interpret
from ..storage import Storage, get_storage
from ..report_service import (
    NullReportGenerator,
    OpenAIReportGenerator,
    ReportGenerator,
    build_facts,
)
from ..saju_service import ELEMENTS, MidnightRule, build_chart, current_period
from ..tone_samples import is_active as tone_is_active
from ..tarot_service import draw, period_seed

router = APIRouter(prefix="/readings", tags=["readings"])


def get_generator() -> ReportGenerator:
    """키가 있으면 실제 생성기, 없으면 계산 결과만 내는 경로 (PRD §11.3).

    FastAPI 의존성으로 주입한다 — 테스트가 이걸 갈아끼워 **네트워크를 타지 않게** 한다.
    테스트가 실제 API 를 호출하면 느려지고 비용이 든다.
    """
    settings = get_settings()
    if settings.openai_api_key and settings.openai_api_key != "CHANGE_ME":
        return OpenAIReportGenerator(
            settings.openai_api_key,
            settings.report_model,
            reasoning_effort=settings.report_reasoning_effort,
            max_completion_tokens=settings.report_max_tokens,
        )
    return NullReportGenerator()


TOPICS = ("재회운", "상대방속마음", "연애", "재물", "대인관계")

# 출생지 → 경도 (PRD §6.1 필드 7). 17개 시·도. 도(道)는 도청 소재지 기준 근사값.
# ⚠️ 프론트 schemas/reading.ts 의 BIRTH_PLACES 와 **이름이 정확히 같아야** 한다.
#    여기서 화이트리스트로 검증하므로 하나라도 다르면 그 지역이 400 으로 막힌다.
BIRTH_PLACES: dict[str, float] = {
    "서울": 126.978,
    "경기(수원)": 127.010,
    "인천": 126.705,
    "강원(춘천)": 127.729,
    "충북(청주)": 127.489,
    "충남(홍성)": 126.661,
    "세종": 127.289,
    "대전": 127.385,
    "전북(전주)": 127.148,
    "전남(무안)": 126.463,
    "광주": 126.851,
    "경북(안동)": 128.729,
    "대구": 128.601,
    "경남(창원)": 128.682,
    "부산": 129.075,
    "울산": 129.311,
    "제주": 126.531,
    "해외·모름": 135.0,
}

MIN_YEAR = 1900


class ReadingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    gender: Literal["남", "여"]
    calendar_type: Literal["solar", "lunar"]
    birth_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    is_leap_month: bool = False
    birth_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    birth_place: str = "서울"
    topics: list[Literal[TOPICS]] = Field(min_length=1, max_length=5)  # type: ignore[valid-type]
    tarot_mode: Literal["auto", "manual"] = "auto"

    @field_validator("name")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        """프롬프트 인젝션 대비 — 개행·제어문자를 걸러낸다 (PRD §12.18)."""
        cleaned = v.strip()
        if not cleaned or any(ord(c) < 32 for c in cleaned):
            raise ValueError("이름에 줄바꿈이나 제어문자를 넣을 수 없습니다.")
        return cleaned

    @field_validator("birth_place")
    @classmethod
    def known_place(cls, v: str) -> str:
        if v not in BIRTH_PLACES:
            raise ValueError("지원하지 않는 출생지입니다.")
        return v

    @field_validator("topics")
    @classmethod
    def unique_topics(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("주제가 중복되었습니다.")
        return v


class PillarOut(BaseModel):
    gan: str
    ji: str
    ko: str


KST = timezone(timedelta(hours=9))


class PeriodOut(BaseModel):
    year_ko: str
    month_ko: str
    label: str


class InputEcho(BaseModel):
    solar_datetime: str
    true_solar_correction_min: int
    dst_applied: bool
    midnight_rule: str
    standard_meridian: float


class ElementsOut(BaseModel):
    목: float
    화: float
    토: float
    금: float
    수: float
    verdict: list[str]


class TarotOut(BaseModel):
    position: str
    position_ko: str
    card: str
    card_ko: str
    reversed: bool
    keywords: list[str]


class PillarsOut(BaseModel):
    year: PillarOut
    month: PillarOut
    day: PillarOut
    hour: PillarOut | None


class InterpretationOut(BaseModel):
    day_master_ko: str
    day_master_gan: str
    day_master_image: str
    element: str
    yin_yang: str
    shishen: dict[str, int]
    dominant: list[str]


class ReportOut(BaseModel):
    saju_reading: list[str]
    monthly_flow: list[str]
    advice: dict[str, str]
    keywords: list[str]
    disclaimer: str


class ReadingResponse(BaseModel):
    id: str
    input_echo: InputEcho
    pillars: PillarsOut
    elements: ElementsOut
    tarot: list[TarotOut]
    interpretation: InterpretationOut
    """사주 풀이 재료 — 일간·십성 (PRD §8.7)"""
    period: PeriodOut
    """이번 달 기운 — 세운·월운. 원국과 달리 달마다 바뀐다 (PRD §8.5)"""
    report: ReportOut | None = None
    """생성 실패·키 없음이면 null — 계산 결과만 보여준다 (PRD §11.3 부분 성공)"""
    report_model: str | None = None
    engine_version: str
    tarot_seed: int
    draft_before_tone_learning: bool = True


def _to_solar(body: ReadingRequest) -> date:
    year, month, day = (int(x) for x in body.birth_date.split("-"))
    if body.calendar_type == "lunar":
        converted = lunar_to_solar(year, month, day, body.is_leap_month)
        return date.fromisoformat(converted.solar_date)
    if year < MIN_YEAR:
        raise CalendarError("YEAR_OUT_OF_RANGE", f"{MIN_YEAR}년 이후만 지원합니다.")
    try:
        return date(year, month, day)
    except ValueError as e:
        raise CalendarError("INVALID_SOLAR_DATE", "없는 날짜입니다.") from e


class ShareOut(BaseModel):
    token: str
    url: str
    expires_at: str | None


class ListItem(BaseModel):
    id: str
    masked_name: str
    gender: str
    created_at: str
    expires_at: str


@router.post("", response_model=ReadingResponse, status_code=201)
def create_reading(
    body: ReadingRequest,
    generator: ReportGenerator = Depends(get_generator),
    storage: Storage = Depends(get_storage),
) -> ReadingResponse:
    solar = _to_solar(body)

    # 시간 미상이면 정오를 기준으로 절기·일주만 잡고 시주는 만들지 않는다 (PRD §8.3)
    known_time = body.birth_time is not None
    hh, mm = (int(x) for x in (body.birth_time or "12:00").split(":"))
    clock = datetime(solar.year, solar.month, solar.day, hh, mm)

    longitude = BIRTH_PLACES[body.birth_place]
    corrected = correct(clock, longitude)

    rule: MidnightRule = "조자시"
    chart = build_chart(
        corrected.jieqi_reference,
        corrected.true_solar if known_time else None,
        midnight_rule=rule,
    )

    reading = interpret(
        corrected.jieqi_reference,
        corrected.true_solar if known_time else None,
        midnight_rule=rule,
    )

    # 이번 달 기운 — 절기 기준으로 바뀐다 (PRD §8.5)
    now = datetime.now(KST).replace(tzinfo=None)
    now_corrected = correct(now, longitude)
    period = current_period(now, now_corrected.jieqi_reference)

    # 같은 사람 + 같은 달이면 항상 같은 카드 (PRD §8.6)
    birth_key = f"{solar.isoformat()}|{body.birth_time or 'unknown'}|{body.birth_place}"
    seed = period_seed(birth_key, f"{period.year.ko}|{period.month.ko}")
    cards = draw(seed)
    tarot_out = [TarotOut(**c.__dict__) for c in cards]

    # 문장 생성 — 실패해도 계산 결과는 그대로 돌려준다 (PRD §11.3)
    facts = build_facts(
        pillars={
            "year": chart.year.__dict__,
            "month": chart.month.__dict__,
            "day": chart.day.__dict__,
            "hour": chart.hour.__dict__ if chart.hour else None,
        },
        elements=chart.elements.counts,
        verdict=chart.elements.verdict,
        tarot=[c.model_dump() for c in tarot_out],
        period=period.label,
        interpretation=reading.summary_facts,
        basis=(
            f"{corrected.clock.isoformat(timespec='minutes')} "
            f"(진태양시 {corrected.true_solar_correction_min}분 보정, "
            f"서머타임 {'적용' if corrected.dst_applied else '미적용'}, {rule} 기준)"
        ),
    )
    report = generator.generate(facts, body.name, list(body.topics))

    response = ReadingResponse(
        id=f"r-{seed:016x}",
        input_echo=InputEcho(
            solar_datetime=corrected.clock.isoformat(timespec="minutes"),
            true_solar_correction_min=corrected.true_solar_correction_min,
            dst_applied=corrected.dst_applied,
            midnight_rule=rule,
            standard_meridian=corrected.standard_meridian,
        ),
        pillars=PillarsOut(
            year=PillarOut(**chart.year.__dict__),
            month=PillarOut(**chart.month.__dict__),
            day=PillarOut(**chart.day.__dict__),
            hour=PillarOut(**chart.hour.__dict__) if chart.hour else None,
        ),
        elements=ElementsOut(
            **{e: chart.elements.counts[e] for e in ELEMENTS},
            verdict=chart.elements.verdict,
        ),
        tarot=tarot_out,
        interpretation=InterpretationOut(
            day_master_ko=reading.day_master.ko,
            day_master_gan=reading.day_master.gan,
            day_master_image=reading.day_master.image,
            element=reading.day_master.element,
            yin_yang=reading.day_master.yin_yang,
            shishen=reading.shishen,
            dominant=reading.dominant,
        ),
        period=PeriodOut(
            year_ko=period.year.ko, month_ko=period.month.ko, label=period.label
        ),
        report=ReportOut(
            saju_reading=report.saju_reading,
            monthly_flow=report.monthly_flow,
            advice=report.advice,
            keywords=report.keywords,
            disclaimer=report.disclaimer,
        )
        if report
        else None,
        report_model=report.model if report else None,
        engine_version=chart.engine_version,
        tarot_seed=seed,
        draft_before_tone_learning=not tone_is_active(),
    )

    # 저장 (PRD §9). 이름·생년월일은 암호화되고, 보관 기간이 지나면 지워진다
    settings = get_settings()
    payload = response.model_dump()
    payload.pop("id", None)
    storage.save(
        response.id,
        name=body.name,
        gender=body.gender,
        birth=f"{body.calendar_type} {body.birth_date} {body.birth_time or '시간미상'}",
        payload=payload,
        retention_days=settings.data_retention_days,
    )
    return response


@router.get("/{reading_id}", response_model=ReadingResponse)
def get_reading(
    reading_id: str = PathParam(min_length=3, max_length=64),
    storage: Storage = Depends(get_storage),
) -> ReadingResponse:
    """링크를 다시 열거나 새로고침할 때. 없거나 기간이 지났으면 404."""
    stored = storage.get(reading_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    return ReadingResponse(id=stored.id, **stored.payload)


@router.delete(
    "/{reading_id}", status_code=204, dependencies=[Depends(require_admin)]
)
def delete_reading(
    reading_id: str = PathParam(min_length=3, max_length=64),
    storage: Storage = Depends(get_storage),
) -> None:
    """삭제 — **X-Admin-Token 필요** (PRD §12.9).

    점검에서 토큰 없이 남의 리포트를 지울 수 있었다. 링크를 받은 사람이
    상담자의 기록을 없앨 수 있으면 안 된다. 손님의 삭제 요청은 상담자를
    거치도록 한다.
    """
    if not storage.delete(reading_id):
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")


@router.post("/{reading_id}/share", response_model=ShareOut, status_code=201)
def create_share(
    reading_id: str = PathParam(min_length=3, max_length=64),
    storage: Storage = Depends(get_storage),
) -> ShareOut:
    """읽기 전용 공유 링크. 토큰은 32자 난수라 추측할 수 없다 (PRD §12.3)."""
    token = storage.create_share(reading_id)
    if token is None:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    return ShareOut(
        token=token,
        url=f"/share/{token}",
        expires_at=None,
    )
