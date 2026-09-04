"""리포트 DB 백업·복원 (PRD §12.17).

백업은 "했다"가 아니라 **"복구된다"** 가 중요하다. 그래서 이 도구는
백업을 만든 뒤 **그 자리에서 열어 검사**하고, 복원 기능을 함께 제공한다.
(픽사·GitLab 둘 다 "백업이 있다고 믿었지만 고장 나 있었다.")

지키는 것
  · **서버가 돌고 있어도 안전하게** 뜬다 — 파일 복사가 아니라 SQLite 백업 API 를 쓴다.
    돌아가는 DB 를 그냥 cp 하면 쓰기 중간 상태가 찍혀 깨진 사본이 나온다.
  · 백업 파일에도 개인정보가 있다 → **AES-256-GCM 으로 암호화**해서 보관한다.
  · 보관 기간이 지난 백업은 지운다(기본 4주).

쓰는 법
    python tools/backup.py                    백업 만들기
    python tools/backup.py --목록              백업 목록 보기
    python tools/backup.py --검증 <파일>       열어서 멀쩡한지만 확인
    python tools/backup.py --복원 <파일>       복원 (덮어쓰지 않고 새 파일로)

암호는 환경변수 BACKUP_PASSPHRASE 로 주거나, 없으면 물어본다.
**이 암호는 이 컴퓨터에 저장하지 않는다.** 비밀번호 관리자에 넣어 둘 것.
"""

from __future__ import annotations

import argparse
import getpass
import io
import json
import os
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "data"
DB_PATH = Path(os.environ.get("DB_PATH") or (DATA / "readings.db"))
KEY_PATH = DATA / "field_key.txt"
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR") or (BACKEND.parent / "backups"))

MAGIC = b"SAJUBAK1"
SALT_LEN, NONCE_LEN = 16, 12
KEEP_DAYS = int(os.environ.get("BACKUP_KEEP_DAYS") or 28)   # 4주 (PRD §12.17)


# ── 암호화 ───────────────────────────────────────────────────

def _derive(passphrase: str, salt: bytes) -> bytes:
    """암호 → 키. scrypt 는 일부러 느리다 — 대입 공격을 어렵게 한다."""
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())


def encrypt(plain: bytes, passphrase: str) -> bytes:
    salt, nonce = os.urandom(SALT_LEN), os.urandom(NONCE_LEN)
    blob = AESGCM(_derive(passphrase, salt)).encrypt(nonce, plain, MAGIC)
    return MAGIC + salt + nonce + blob


def decrypt(data: bytes, passphrase: str) -> bytes:
    if not data.startswith(MAGIC):
        raise ValueError("이 도구가 만든 백업 파일이 아닙니다.")
    head = len(MAGIC)
    salt = data[head:head + SALT_LEN]
    nonce = data[head + SALT_LEN:head + SALT_LEN + NONCE_LEN]
    blob = data[head + SALT_LEN + NONCE_LEN:]
    try:
        return AESGCM(_derive(passphrase, salt)).decrypt(nonce, blob, MAGIC)
    except InvalidTag:
        # 암호가 틀렸거나 파일이 손상됐다. 둘을 구분할 방법은 없다 —
        # 구분하려면 암호 확인용 값을 따로 저장해야 하는데 그게 공격 단서가 된다.
        raise SystemExit(
            "  ✗ 열지 못했습니다.\n"
            "    암호가 틀렸거나, 파일이 손상됐습니다.\n"
            "    암호를 다시 확인하고, 맞다면 다른 백업 파일을 시도하세요."
        ) from None


def ask_passphrase(confirm: bool = False) -> str:
    env = os.environ.get("BACKUP_PASSPHRASE")
    if env:
        return env
    if not sys.stdin.isatty():
        raise SystemExit("암호가 필요합니다. BACKUP_PASSPHRASE 환경변수로 주세요.")
    pw = getpass.getpass("  백업 암호: ")
    if not pw:
        raise SystemExit("암호가 비어 있습니다.")
    if confirm and pw != getpass.getpass("  한 번 더: "):
        raise SystemExit("두 번 입력한 암호가 다릅니다.")
    return pw


# ── 사본 뜨기 ────────────────────────────────────────────────

def snapshot(dest: Path) -> None:
    """돌아가는 DB 에서 안전하게 사본을 뜬다.

    파일 복사가 아니라 SQLite 의 백업 API 를 쓴다. 서버가 쓰는 중이어도
    일관된 시점의 사본이 나온다.
    """
    src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        out = sqlite3.connect(dest)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()


def inspect(path: Path) -> dict:
    """사본이 진짜 멀쩡한지 열어서 확인한다."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(f"백업 파일이 깨졌습니다: {ok}")
        counts = {}
        for table in ("readings", "share_links"):
            counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return counts
    finally:
        con.close()


# ── 백업 ─────────────────────────────────────────────────────

def make_backup(include_key: bool) -> Path:
    if not DB_PATH.exists():
        raise SystemExit(f"DB 가 없습니다: {DB_PATH}")

    passphrase = ask_passphrase(confirm=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")

    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "readings.db"
        snapshot(copy)
        counts = inspect(copy)                       # 뜨자마자 검사한다

        meta = {
            "만든시각": datetime.now().isoformat(timespec="seconds"),
            "원본": str(DB_PATH),
            "건수": counts,
            "필드키포함": include_key,
        }

        bundle = io.BytesIO()
        with tarfile.open(fileobj=bundle, mode="w:gz") as tar:
            tar.add(copy, arcname="readings.db")
            info = tarfile.TarInfo("meta.json")
            raw = json.dumps(meta, ensure_ascii=False, indent=2).encode()
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
            if include_key and KEY_PATH.exists():
                tar.add(KEY_PATH, arcname="field_key.txt")

        out = BACKUP_DIR / f"saju-{stamp}.saju.enc"
        out.write_bytes(encrypt(bundle.getvalue(), passphrase))

    print(f"  ✓ 백업 완료  {out}")
    print(f"    리포트 {counts['readings']}건 · 공유링크 {counts['share_links']}건 "
          f"· {out.stat().st_size / 1024:.0f}KB")
    if include_key:
        print("    필드 암호화 키를 함께 넣었습니다 — 이 파일 하나로 복원됩니다.")
    else:
        print("    ! 필드 키는 넣지 않았습니다. field_key.txt 를 따로 보관해야 복원됩니다.")
    return out


def prune() -> int:
    """보관 기간이 지난 백업을 지운다."""
    if not BACKUP_DIR.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    for f in BACKUP_DIR.glob("saju-*.saju.enc"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            removed += 1
    if removed:
        print(f"  {KEEP_DAYS}일이 지난 백업 {removed}개를 지웠습니다.")
    return removed


# ── 검증·복원 ────────────────────────────────────────────────

def _open_archive(path: Path, passphrase: str):
    if not path.is_file():
        raise SystemExit(
            f"  ✗ 그런 파일이 없습니다: {path}\n"
            "    --목록 으로 백업 목록을 확인하세요."
        )
    bundle = decrypt(path.read_bytes(), passphrase)
    return tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz")


def verify(path: Path) -> None:
    """복원하지 않고 '진짜 열리는지'만 확인한다 (PRD §12.17 복구 테스트)."""
    passphrase = ask_passphrase()
    with tempfile.TemporaryDirectory() as tmp, _open_archive(path, passphrase) as tar:
        meta = json.loads(tar.extractfile("meta.json").read().decode())
        tar.extract("readings.db", tmp, filter="data")
        counts = inspect(Path(tmp) / "readings.db")

    print(f"  ✓ 열립니다  {path.name}")
    print(f"    만든 때  : {meta['만든시각']}")
    print(f"    담긴 것  : 리포트 {counts['readings']}건 · 공유링크 {counts['share_links']}건")
    print(f"    필드 키  : {'포함' if meta.get('필드키포함') else '없음 (따로 보관 필요)'}")
    if counts != meta["건수"]:
        print("    ! 기록된 건수와 실제가 다릅니다. 확인이 필요합니다.")


def restore(path: Path) -> None:
    """복원한다. **덮어쓰지 않는다** — 새 파일로 꺼내고 사람이 옮긴다."""
    passphrase = ask_passphrase()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = BACKUP_DIR / f"복원-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with _open_archive(path, passphrase) as tar:
        tar.extractall(out_dir, filter="data")
    counts = inspect(out_dir / "readings.db")

    print(f"  ✓ 복원 완료  {out_dir}")
    print(f"    리포트 {counts['readings']}건 · 공유링크 {counts['share_links']}건")
    print()
    print("  운영에 반영하려면 서버를 끄고 아래를 직접 옮기세요 (덮어쓰기라 자동으로 하지 않습니다):")
    print(f"    {out_dir / 'readings.db'}")
    print(f"      → {DB_PATH}")
    if (out_dir / "field_key.txt").exists():
        print(f"    {out_dir / 'field_key.txt'}")
        print(f"      → {KEY_PATH}")
        print("    (필드 키가 다르면 이름·생년월일을 복호화하지 못합니다)")


def show_list() -> None:
    files = sorted(BACKUP_DIR.glob("saju-*.saju.enc"), reverse=True) if BACKUP_DIR.exists() else []
    if not files:
        print(f"  백업이 없습니다. ({BACKUP_DIR})")
        return
    print(f"  {BACKUP_DIR}")
    for f in files:
        age = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days
        print(f"    {f.name:<28} {f.stat().st_size/1024:>7.0f}KB   {age}일 전")
    print(f"\n  총 {len(files)}개 · {KEEP_DAYS}일이 지나면 자동으로 지워집니다.")


def main() -> None:
    # 에러 메시지도 사람이 읽을 수 있어야 한다. stderr 까지 맞춰 두지 않으면
    # 윈도우 콘솔(cp949)에서 한글이 깨지고 기호가 ✗ 처럼 나온다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="리포트 DB 백업·복원 (PRD §12.17)")
    ap.add_argument("--목록", action="store_true", help="백업 목록 보기")
    ap.add_argument("--검증", metavar="파일", help="열어서 멀쩡한지 확인")
    ap.add_argument("--복원", metavar="파일", help="새 폴더로 꺼내기")
    ap.add_argument("--키제외", action="store_true",
                    help="필드 암호화 키를 백업에 넣지 않는다 (따로 보관할 때)")
    args = ap.parse_args()

    print()
    if args.목록:
        return show_list()
    if args.검증:
        return verify(Path(args.검증))
    if args.복원:
        return restore(Path(args.복원))

    make_backup(include_key=not args.키제외)
    prune()
    print()
    print("  3-2-1 규칙 — 이 파일을 다른 매체와 다른 장소에도 한 벌 두세요.")
    print("  분기에 한 번은 --검증 으로 진짜 열리는지 확인하세요.")


if __name__ == "__main__":
    main()
