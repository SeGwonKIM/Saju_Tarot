"""저장·공유·보관기간 (PRD §9, §12.9, §12.14)."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.crypto import FieldCipher, mask_name
from app.main import app
from app.storage import Storage, get_storage

client = TestClient(app)

BODY = {
    "name": "홍길동",
    "gender": "여",
    "calendar_type": "solar",
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "birth_place": "서울",
    "topics": ["연애"],
    "tarot_mode": "auto",
}


@pytest.fixture
def store(tmp_path):
    return Storage(db_path=tmp_path / "t.db")


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path):
    """테스트가 실제 DB 를 건드리지 않게 한다."""
    s = Storage(db_path=tmp_path / "api.db")
    app.dependency_overrides[get_storage] = lambda: s
    yield s
    app.dependency_overrides.pop(get_storage, None)


# ── 암호화 (PRD §12.14) ───────────────────────────────────────


def test_name_is_encrypted_at_rest(store, tmp_path):
    store.save("r-1", name="홍길동", gender="여", birth="solar 1990-01-01 12:00",
               payload={"a": 1}, retention_days=90)
    raw = (tmp_path / "t.db").read_bytes()
    assert "홍길동".encode() not in raw, "이름이 평문으로 저장됐다"
    assert "1990-01-01".encode() not in raw, "생년월일이 평문으로 저장됐다"
    assert store.get("r-1").name == "홍길동"  # 읽을 때는 복원된다


def test_cipher_roundtrip(tmp_path, monkeypatch):
    from app import crypto

    monkeypatch.setattr(crypto, "KEY_PATH", tmp_path / "k.txt")
    c = FieldCipher()
    assert c.decrypt(c.encrypt("홍길동")) == "홍길동"
    assert c.encrypt("홍길동") != c.encrypt("홍길동")  # nonce 가 매번 다르다


@pytest.mark.parametrize(
    "name,masked", [("홍길동", "홍*동"), ("김철", "김*"), ("이", "이"), ("남궁민수", "남**수")]
)
def test_name_masking(name, masked):
    assert mask_name(name) == masked


# ── 저장·조회 ─────────────────────────────────────────────────


def test_reading_survives_refresh():
    """탭을 닫았다 다시 열어도 리포트가 남아 있어야 한다."""
    created = client.post("/api/v1/readings", json=BODY).json()
    again = client.get(f"/api/v1/readings/{created['id']}")
    assert again.status_code == 200
    assert again.json()["pillars"] == created["pillars"]
    assert again.json()["tarot"] == created["tarot"]


def test_missing_reading_is_404():
    assert client.get("/api/v1/readings/r-없는것").status_code == 404


def test_delete_removes_it():
    rid = client.post("/api/v1/readings", json=BODY).json()["id"]
    assert client.delete(f"/api/v1/readings/{rid}").status_code == 204
    assert client.get(f"/api/v1/readings/{rid}").status_code == 404


# ── 공유 링크 (PRD §12.3) ─────────────────────────────────────


def test_share_link_opens_readonly():
    rid = client.post("/api/v1/readings", json=BODY).json()["id"]
    share = client.post(f"/api/v1/readings/{rid}/share").json()
    assert len(share["token"]) >= 32, "토큰이 짧으면 추측당한다"

    shared = client.get(f"/api/v1/share/{share['token']}")
    assert shared.status_code == 200
    assert shared.json()["payload"]["pillars"]


def test_shared_payload_has_no_personal_info():
    """링크가 퍼져도 이름·생년월일은 나가지 않는다 (PRD §12.14)."""
    rid = client.post("/api/v1/readings", json=BODY).json()["id"]
    token = client.post(f"/api/v1/readings/{rid}/share").json()["token"]
    body = client.get(f"/api/v1/share/{token}").text
    assert "홍길동" not in body
    assert "1990-01-01" not in body


def test_unknown_token_is_404():
    assert client.get("/api/v1/share/" + "x" * 32).status_code == 404


def test_expired_share_is_404_like_missing(store):
    """만료와 부재를 구분하면 존재 여부가 샌다 (PRD §10.6)."""
    store.save("r-2", name="홍길동", gender="여", birth="b", payload={}, retention_days=90)
    token = store.create_share("r-2", expires_in_days=-1)  # 이미 지난 링크
    assert store.get_by_share(token) is None


def test_share_of_missing_reading_returns_none(store):
    assert store.create_share("없는id") is None


# ── 보관 기간 (PRD §12.9) ─────────────────────────────────────


def test_expired_reading_is_not_returned(store):
    store.save("r-3", name="홍길동", gender="여", birth="b", payload={}, retention_days=-1)
    assert store.get("r-3") is None


def test_purge_deletes_hard(store, tmp_path):
    store.save("r-4", name="홍길동", gender="여", birth="b", payload={}, retention_days=-1)
    assert store.purge_expired() == 1
    raw = (tmp_path / "t.db").read_bytes()
    assert b"r-4" not in raw, "soft delete 가 아니라 하드 삭제여야 한다"


def test_purge_keeps_live_ones(store):
    store.save("live", name="A", gender="남", birth="b", payload={}, retention_days=90)
    store.save("dead", name="B", gender="여", birth="b", payload={}, retention_days=-1)
    store.purge_expired()
    assert store.get("live") is not None
    assert store.get("dead") is None


def test_expiry_follows_retention_setting(store):
    r = store.save("r-5", name="A", gender="남", birth="b", payload={}, retention_days=90)
    assert timedelta(days=89) < (r.expires_at - datetime.now()) < timedelta(days=91)


# ── 목록 (PRD §12.14 마스킹) ──────────────────────────────────


def test_list_masks_names():
    client.post("/api/v1/readings", json=BODY)
    items = client.get("/api/v1/readings-list").json()
    assert items
    assert items[0]["masked_name"] == "홍*동"
    assert "홍길동" not in client.get("/api/v1/readings-list").text
