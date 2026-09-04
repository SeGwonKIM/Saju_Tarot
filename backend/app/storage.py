"""리포트 저장 (PRD §9, §12.14, §12.9).

내 PC 서버 구성이라 SQLite 를 쓴다 — 외부 서비스도 키도 필요 없고
백업이 파일 하나다. 클라우드로 옮길 때를 위해 이 모듈 밖에서는
SQL 을 모르게 막아 뒀다(교체 지점이 여기 하나).

지키는 것
  · 이름·생년월일·시각은 **암호화해서** 저장한다 (§12.14)
  · 보관 기간이 지나면 지운다 — 하드 삭제, soft delete 없음 (§12.9)
  · 공유 토큰은 32자 난수. 순번 id 를 링크에 쓰지 않는다 (§12.3)
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .crypto import DecryptionFailed, FieldCipher, mask_name

log = logging.getLogger("saju.storage")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "readings.db"
SHARE_TOKEN_BYTES = 24  # base64url 로 32자

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id            TEXT PRIMARY KEY,
    name_enc      TEXT NOT NULL,
    birth_enc     TEXT NOT NULL,
    gender        TEXT NOT NULL,
    payload       TEXT NOT NULL,   -- 계산 결과·리포트 (개인 식별 정보 제외)
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_readings_expires ON readings(expires_at);

CREATE TABLE IF NOT EXISTS share_links (
    token       TEXT PRIMARY KEY,
    reading_id  TEXT NOT NULL REFERENCES readings(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT,
    view_count  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_share_reading ON share_links(reading_id);
"""


def redact_for_share(payload: dict[str, Any]) -> dict[str, Any]:
    """공유 링크로 나갈 때 개인 식별 값을 뺀다 (PRD §12.14).

    링크는 단톡방으로 전달될 수 있다. 계산 결과는 보여주되
    **생년월일시는 내보내지 않는다** — 그것만으로 사람이 특정된다.
    보정값·자시 기준 같은 계산 근거는 남긴다(검증에 필요하다).
    """
    shared = json.loads(json.dumps(payload, ensure_ascii=False))
    echo = shared.get("input_echo")
    if isinstance(echo, dict):
        echo.pop("solar_datetime", None)
    return shared


@dataclass(frozen=True)
class StoredReading:
    id: str
    name: str
    gender: str
    birth: str
    payload: dict[str, Any]
    created_at: datetime
    expires_at: datetime

    @property
    def masked_name(self) -> str:
        return mask_name(self.name)


class Storage:
    def __init__(self, db_path: Path | None = None, env_key: str = "") -> None:
        self._path = db_path or DB_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._cipher = FieldCipher(env_key)
        with self._connect() as con:
            con.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        # 지운 내용을 0으로 덮어쓴다. 이게 없으면 DELETE 후에도 파일에 원문이 남는다
        # (테스트가 실제로 잡아냈다 — PRD §12.9 "하드 삭제")
        con.execute("PRAGMA secure_delete = ON")
        return con

    # ── 저장·조회 ─────────────────────────────────────────────

    def save(
        self,
        reading_id: str,
        *,
        name: str,
        gender: str,
        birth: str,
        payload: dict[str, Any],
        retention_days: int,
    ) -> StoredReading:
        now = datetime.now()
        expires = now + timedelta(days=retention_days)
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO readings"
                " (id, name_enc, birth_enc, gender, payload, created_at, expires_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    reading_id,
                    self._cipher.encrypt(name),
                    self._cipher.encrypt(birth),
                    gender,
                    json.dumps(payload, ensure_ascii=False),
                    now.isoformat(timespec="seconds"),
                    expires.isoformat(timespec="seconds"),
                ),
            )
        return StoredReading(
            id=reading_id, name=name, gender=gender, birth=birth,
            payload=payload, created_at=now, expires_at=expires,
        )

    def get(self, reading_id: str) -> StoredReading | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM readings WHERE id = ?", (reading_id,)
            ).fetchone()
        return self._to_reading(row)

    def _to_reading(self, row: sqlite3.Row | None) -> StoredReading | None:
        if row is None:
            return None
        expires = datetime.fromisoformat(row["expires_at"])
        if expires < datetime.now():
            # 보관 기간이 지난 것은 없는 것으로 본다. 정리 작업이 곧 지운다
            return None
        try:
            name = self._cipher.decrypt(row["name_enc"])
            birth = self._cipher.decrypt(row["birth_enc"])
        except DecryptionFailed:
            log.warning("복호화 실패 — 키가 바뀌었을 수 있습니다 (id=%s)", row["id"])
            return None
        return StoredReading(
            id=row["id"], name=name, gender=row["gender"], birth=birth,
            payload=json.loads(row["payload"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=expires,
        )

    def recent(self, limit: int = 30) -> list[StoredReading]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM readings WHERE expires_at > ?"
                " ORDER BY created_at DESC LIMIT ?",
                (datetime.now().isoformat(timespec="seconds"), limit),
            ).fetchall()
        return [r for r in (self._to_reading(row) for row in rows) if r]

    def delete(self, reading_id: str) -> bool:
        with self._connect() as con:
            cur = con.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        if cur.rowcount:
            with self._connect() as con:
                con.execute("VACUUM")
        return cur.rowcount > 0

    # ── 공유 링크 ─────────────────────────────────────────────

    def create_share(self, reading_id: str, expires_in_days: int | None = 30) -> str | None:
        if self.get(reading_id) is None:
            return None
        token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
        expires = (
            (datetime.now() + timedelta(days=expires_in_days)).isoformat(timespec="seconds")
            if expires_in_days
            else None
        )
        with self._connect() as con:
            con.execute(
                "INSERT INTO share_links (token, reading_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (token, reading_id, datetime.now().isoformat(timespec="seconds"), expires),
            )
        return token

    def get_by_share(self, token: str) -> StoredReading | None:
        """만료된 링크와 없는 링크를 구분하지 않는다 — 존재 여부가 새면 안 된다 (§10.6)."""
        with self._connect() as con:
            row = con.execute(
                "SELECT reading_id, expires_at FROM share_links WHERE token = ?", (token,)
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now():
                return None
            con.execute(
                "UPDATE share_links SET view_count = view_count + 1 WHERE token = ?",
                (token,),
            )
        return self.get(row["reading_id"])

    # ── 보관 기간 정리 (PRD §12.9) ────────────────────────────

    def purge_expired(self) -> int:
        """기간이 지난 리포트를 **하드 삭제**한다. soft delete 는 두지 않는다."""
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute("DELETE FROM readings WHERE expires_at < ?", (now,))
            con.execute(
                "DELETE FROM share_links WHERE reading_id NOT IN (SELECT id FROM readings)"
            )
        if cur.rowcount:
            # VACUUM 으로 빈 페이지를 회수한다. secure_delete 와 함께여야 흔적이 사라진다
            with self._connect() as con:
                con.execute("VACUUM")
            log.info("보관 기간이 지난 리포트 %d건을 삭제했습니다", cur.rowcount)
        return cur.rowcount


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        from .config import get_settings

        _storage = Storage(env_key=get_settings().field_encryption_key)
    return _storage
