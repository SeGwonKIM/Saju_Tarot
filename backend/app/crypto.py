"""개인정보 필드 암호화 (PRD §12.14).

이름·생년월일·시각은 개인 식별이 가능한 값이다. DB 파일이 통째로 새더라도
이 값들은 읽히지 않아야 한다.

  AES-256-GCM · 필드마다 새 nonce · 저장 형식은 base64(nonce + ciphertext)

키 우선순위
  1) 환경변수 FIELD_ENCRYPTION_KEY (운영·클라우드에서 권장)
  2) backend/data/field_key.txt — 없으면 첫 실행 때 만든다 (내 PC 서버용)

키 파일은 .gitignore 로 막혀 있다. **이 파일을 잃으면 저장된 리포트를 복호화할 수 없다.**
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import logging
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("saju.crypto")

KEY_PATH = Path(__file__).resolve().parents[1] / "data" / "field_key.txt"
NONCE_BYTES = 12


class DecryptionFailed(Exception):
    """키가 바뀌었거나 값이 손상됐다."""


def _load_or_create_key(env_key: str = "") -> bytes:
    if env_key and env_key != "CHANGE_ME":
        return base64.b64decode(env_key)

    if KEY_PATH.exists():
        return base64.b64decode(KEY_PATH.read_text(encoding="utf-8").strip())

    key = AESGCM.generate_key(bit_length=256)
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_text(base64.b64encode(key).decode(), encoding="utf-8")
    log.warning(
        "개인정보 암호화 키를 새로 만들었습니다: %s — 이 파일을 잃으면 "
        "저장된 리포트를 읽을 수 없습니다. 백업해 두세요.",
        KEY_PATH,
    )
    return key


class FieldCipher:
    def __init__(self, env_key: str = "") -> None:
        self._key = _load_or_create_key(env_key)
        self._aes = AESGCM(self._key)

    def fingerprint(self, value: str) -> str:
        """같은 값인지 **대조만** 할 수 있는 지문을 만든다.

        암호화 키로 HMAC 을 건다. 그냥 해시로 두면 안 된다 — 생년월일은
        경우의 수가 적어서, DB 만 새어도 훑어서 원래 값을 찾아낼 수 있다
        (실제로 타로 seed 로 1.6초 만에 복원한 적이 있다, PRD v3.1 ⑪).
        키가 없으면 대입해도 맞출 수 없다.
        """
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(NONCE_BYTES)
        blob = nonce + self._aes.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(blob).decode()

    def decrypt(self, stored: str) -> str:
        try:
            blob = base64.b64decode(stored)
            return self._aes.decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], None).decode()
        except (InvalidTag, ValueError, IndexError) as e:
            raise DecryptionFailed("복호화에 실패했습니다 — 키가 바뀌었을 수 있습니다.") from e


def mask_name(name: str) -> str:
    """목록에 보일 이름 — 홍길동 → 홍*동 (PRD §12.14)."""
    if len(name) <= 1:
        return name
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]
