"""사주·타로 리포트 API — 1단계 스캐폴드.

PRD §10 의 계약을 따른다. 지금은 /health 만 열려 있다.
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .logging_setup import setup_logging

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


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """콜드 스타트 예열용 (PRD §10.3, §13)."""
    return {"status": "ok", "env": settings.app_env}
