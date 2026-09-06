"""사주·타로 리포트 API — 1단계 스캐폴드.

PRD §10 의 계약을 따른다. 지금은 /health 만 열려 있다.
"""

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .calendar_service import CalendarError
from .config import get_settings
from .logging_setup import mask_path, setup_logging
from . import rate_limit
from .routers import calendar as calendar_router
from .routers import readings as readings_router
from .routers import share as share_router

settings = get_settings()          # ← 환경변수가 잘못되면 여기서 부팅 실패
setup_logging()
log = logging.getLogger("saju")

app = FastAPI(
    title="사주·타로 상담 리포트 API",
    version="0.1.0",
    # 운영에서는 API 문서와 명세를 모두 닫는다.
    # docs_url 만 닫으면 /openapi.json 으로 엔드포인트·스키마가 그대로 새어 나간다.
    docs_url="/docs" if settings.app_env == "local" else None,
    openapi_url="/openapi.json" if settings.app_env == "local" else None,
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


# 화면이 쓰는 외부 출처 — 폰트(구글·jsdelivr) 외에는 막는다
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
    "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
    "img-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",      # 다른 사이트가 우리를 iframe 으로 감싸지 못하게
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
])

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": CSP,
    # 터널·프록시가 HTTPS 를 씌우므로 브라우저에 HTTPS 고정을 지시한다
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # 공유 링크가 검색엔진에 올라가면 안 된다 (PRD §12.14)
    "X-Robots-Tag": "noindex, nofollow",
}


def _error(status: int, code: str, message: str, field: str | None = None) -> JSONResponse:
    """에러 응답을 한 형태로 통일한다 (PRD §10.6)."""
    payload: dict[str, object] = {"code": code, "message": message}
    if field:
        payload["field"] = field
    return JSONResponse(status_code=status, content={"error": payload})


# 우리가 받는 가장 큰 요청도 1KB 를 넘지 않는다. 넉넉히 잡아도 이 정도면 충분하다.
MAX_BODY_BYTES = 64 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """큰 본문 하나로 집 PC 메모리를 고갈시키지 못하게 한다.

    uvicorn 에는 기본 상한이 없다. 공개 서버에서는 이게 곧 DoS 통로가 된다.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return _error(413, "PAYLOAD_TOO_LARGE", "요청이 너무 큽니다.")
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """PRD §12.4. 요구사항으로 적어두고 구현이 빠져 있었다 — 점검에서 발견."""
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    # 서버 종류를 알리지 않는다 — 알려진 취약점 탐색의 출발점이 된다
    response.headers["Server"] = "saju"
    return response


@app.middleware("http")
async def limit_costly_requests(request: Request, call_next):
    """비용이 드는 요청만 죈다 (PRD §12.5). 공개 서버에서는 필수다."""
    if rate_limit.is_write(request):
        allowed, retry_after = rate_limit.check_write(request)
        if not allowed:
            log.warning("쓰기 한도 초과 %s", mask_path(request.url.path))
            return rate_limit.too_many(retry_after)

    if rate_limit.is_costly(request):
        allowed, retry_after = rate_limit.check(request)
        if not allowed:
            log.warning("레이트리밋 차단 %s", request.url.path)
            return rate_limit.too_many(retry_after)
    return await call_next(request)


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
        mask_path(request.url.path),
        response.status_code,
        elapsed_ms,
        trace_id,
    )
    response.headers["X-Trace-Id"] = trace_id
    return response


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
app.include_router(share_router.router, prefix="/api/v1")


@app.on_event("startup")
def purge_expired_on_start() -> None:
    """보관 기간이 지난 리포트를 정리한다 (PRD §12.9).

    내 PC 서버는 매일 도는 크론이 없으므로 켤 때마다 한 번 훑는다.
    """
    from .storage import get_storage

    try:
        removed = get_storage().purge_expired()
        if removed:
            log.info("기간 만료 리포트 %d건 정리", removed)
    except Exception as e:  # noqa: BLE001 — 정리 실패가 기동을 막으면 안 된다
        log.warning("만료 정리 실패: %s", type(e).__name__)


# ── 화면 서빙 (PRD §14.6 단일 오리진) ────────────────────────
#  프론트 빌드 결과를 같은 서버가 내보낸다. 주소가 하나가 되어
#  터널링이 단순해지고 CORS 문제가 사라진다.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """API 가 아닌 주소는 전부 화면으로 — 새로고침해도 라우팅이 살아 있게."""
        candidate = (DIST / full_path).resolve()
        if full_path and candidate.is_file() and DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
else:
    log.warning("frontend/dist 가 없습니다. `npm run build` 후 다시 켜면 화면이 함께 서빙됩니다.")
