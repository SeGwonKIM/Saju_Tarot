"""상담자 전용 접근 (PRD §12.3 인가).

`/readings-list` 는 **모든 손님의 리포트 id 를 내주는** 창구다.
누구나 부를 수 있으면 id 를 받아 `/readings/{id}` 로 전체 내용을 볼 수 있다
(생년월일시 포함). 점검에서 실제로 그 경로가 뚫려 있었다.

혼자 쓰는 서버라 계정 체계 대신 **관리자 토큰 하나**로 막는다.
  · 환경변수 ADMIN_TOKEN 이 있으면 그 값
  · 없으면 첫 실행에 backend/data/admin_token.txt 를 만들고 로그에 알린다

토큰이 없는 요청은 404 로 돌려보낸다 — 401 이면 "여기 뭔가 있다"를 알려주는 셈이다.
"""

from __future__ import annotations

import hmac
import logging
import secrets
from pathlib import Path

from fastapi import Header, HTTPException

log = logging.getLogger("saju.admin")

TOKEN_PATH = Path(__file__).resolve().parents[1] / "data" / "admin_token.txt"


def _load_or_create_token(env_token: str = "") -> str:
    if env_token and env_token != "CHANGE_ME":
        return env_token
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()

    token = secrets.token_urlsafe(24)
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token, encoding="utf-8")
    log.warning("상담자 토큰을 새로 만들었습니다: %s (파일 내용 참고)", TOKEN_PATH)
    return token


def admin_token() -> str:
    from .config import get_settings

    return _load_or_create_token(get_settings().admin_token)


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """토큰이 맞지 않으면 404 — 존재 자체를 알리지 않는다."""
    expected = admin_token()
    # 타이밍 공격을 피해 상수 시간 비교
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=404, detail="없는 페이지입니다.")
