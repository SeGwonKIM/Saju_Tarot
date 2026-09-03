"""사주·타로 리포트 API — 1단계 스캐폴드.

PRD §10 의 계약을 따른다. 지금은 /health 만 열려 있다.
"""

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .calendar_service import CalendarError
from .config import get_settings
from .logging_setup import setup_logging
from .routers import calendar as calendar_router
from .routers import readings as readings_router

settings = get_settings()          # ← 환경변수가 잘못되면 여기서 부팅 실패
setup_logging()
log = logging.getLogger("saju")

app = FastAPI(
    title="사주·타로 상담 리포트 API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "local" else None,   # 운영에선 문서 비공개
    redoc_url=None,
)

# CORS — 내 프론트 도메인만 (PRD §12.4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def trace_and_log(request: Request, call_next):
    """요청 본문은 로그에 남기지 않는다 (PRD §12.15)."""
    trace_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error trace_id=%s", trace_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "잠시 후 다시 시도해 주세요.",
                    "trace_id": trace_id,
                }
            },
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    log.info(
        "%s %s %s %.1fms trace_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        trace_id,
    )
    response.headers["X-Trace-Id"] = trace_id
    return response


def _error(status: int, code: str, message: str, field: str | None = None) -> JSONResponse:
    """에러 응답을 한 형태로 통일한다 (PRD §10.6)."""
    payload: dict[str, object] = {"code": code, "message": message}
    if field:
        payload["field"] = field
    return JSONResponse(status_code=status, content={"error": payload})


@app.exception_handler(CalendarError)
async def calendar_error_handler(_: Request, exc: CalendarError) -> JSONResponse:
    """형식은 맞지만 도메인상 불가능한 날짜 → 422 (PRD §10.6)."""
    return _error(422, exc.code, exc.message, exc.field)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """입력 형식 오류 → 400. FastAPI 기본값은 422지만 명세를 따른다."""
    first = exc.errors()[0] if exc.errors() else {}
    loc = [str(p) for p in first.get("loc", []) if p not in ("body", "path", "query")]
    return _error(
        400,
        "INVALID_INPUT",
        "입력값을 다시 확인해 주세요.",
        loc[-1] if loc else None,
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return _error(exc.status_code, "HTTP_ERROR", str(exc.detail))


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """콜드 스타트 예열용 (PRD §10.3, §13)."""
    return {"status": "ok", "env": settings.app_env}


app.include_router(calendar_router.router, prefix="/api/v1")
app.include_router(readings_router.router, prefix="/api/v1")
