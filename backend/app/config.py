"""설정 로딩 — 유출 차단 4차 방어 (PRD §12.11 ④).

필수 환경변수가 없거나 형식이 틀리면 **서버가 부팅되지 않는다.**
잘못된 설정으로 서비스가 떠 있는 상태 자체를 막기 위한 것이다.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "production"] = "local"

    # ── CORS (PRD §12.4) — 와일드카드 금지 ──────────────────
    allowed_origins: str = "http://localhost:5173"

    # ── 개인정보 보관 기간 (PRD §12.9) ──────────────────────
    data_retention_days: int = Field(default=90, ge=1, le=365)
    anon_retention_days: int = Field(default=7, ge=1, le=90)

    # ── 비밀값 (PRD §12.10 대장) ────────────────────────────
    #  1단계에서는 아직 붙이지 않으므로 기본값 빈 문자열.
    #  각 기능이 붙는 단계에서 require_secret() 으로 존재를 강제한다.
    anthropic_api_key: str = ""
    # 문장 생성 공급자 — 지금은 OpenAI 키로 진행한다 (PRD §4.7)
    openai_api_key: str = ""
    report_model: str = "gpt-5.5"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    field_encryption_key: str = ""
    database_url: str = ""

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @field_validator("allowed_origins")
    @classmethod
    def no_wildcard(cls, v: str) -> str:
        if "*" in v:
            raise ValueError(
                "ALLOWED_ORIGINS 에 와일드카드(*)는 쓸 수 없습니다. "
                "허용할 프론트 도메인을 명시하세요. (PRD §12.4)"
            )
        return v

    def require_secret(self, name: str) -> str:
        """비밀값이 필요한 기능이 켜질 때 호출한다. 없으면 즉시 실패."""
        value = getattr(self, name, "")
        if not value or value == "CHANGE_ME":
            raise RuntimeError(
                f"환경변수 {name.upper()} 가 설정되지 않았습니다. "
                f".env(로컬) 또는 배포 플랫폼 설정에 넣으세요. (PRD §12.10)"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
