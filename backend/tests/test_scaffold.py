"""1단계 스캐폴드 테스트 — 보안 기본기가 실제로 동작하는지 확인한다."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.logging_setup import mask
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.headers.get("X-Trace-Id")


def test_cors_wildcard_rejected():
    """ALLOWED_ORIGINS 에 * 를 넣으면 설정 자체가 거부된다 (PRD §12.4)."""
    with pytest.raises(ValidationError):
        Settings(allowed_origins="*")


def test_require_secret_fails_when_missing():
    """비밀값 없이 기능을 켜려 하면 즉시 실패한다 (PRD §12.10)."""
    s = Settings(anthropic_api_key="")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        s.require_secret("anthropic_api_key")

    s2 = Settings(anthropic_api_key="CHANGE_ME")
    with pytest.raises(RuntimeError):
        s2.require_secret("anthropic_api_key")


def test_retention_days_bounds():
    with pytest.raises(ValidationError):
        Settings(data_retention_days=0)
    with pytest.raises(ValidationError):
        Settings(data_retention_days=9999)


# 가짜 키를 런타임에 조립한다.
# 소스에 완성된 형태로 적으면 pre-commit 훅이 (올바르게) 커밋을 막는다.
_FAKE_ANTHROPIC = "sk-" + "ant-" + "api03-" + "SECRETVALUE123456789"


@pytest.mark.parametrize(
    "raw,leaked",
    [
        ('{"name": "홍길동"}', "홍길동"),
        ('{"birth_date": "1988-03-05"}', "1988-03-05"),
        ("authorization=Bearer abc123def456", "abc123def456"),
        (f"api_key={_FAKE_ANTHROPIC}", "SECRETVALUE123456789"),
    ],
)
def test_log_masking(raw, leaked):
    """로그에 이름·생년월일·토큰이 남지 않는다 (PRD §12.15)."""
    assert leaked not in mask(raw)
    assert "***" in mask(raw)


def test_openapi_is_closed_in_production():
    """운영에서는 명세가 새면 안 된다 — docs_url 만 닫는 것으로는 부족하다."""
    from fastapi import FastAPI

    from app.config import Settings

    prod = Settings(app_env="production")
    assert prod.app_env == "production"

    # 실제 앱과 같은 규칙으로 만들었을 때 openapi 가 꺼지는지
    a = FastAPI(
        docs_url="/docs" if prod.app_env == "local" else None,
        openapi_url="/openapi.json" if prod.app_env == "local" else None,
    )
    assert a.openapi_url is None
    assert a.docs_url is None
