"""환경변수에 넣은 키가 제대로 읽히고 살아있는지 확인한다.

키 값을 절대 전체 출력하지 않는다 — 앞 12자만 보이고 나머지는 마스킹한다 (PRD §12.15).
로그·터미널 캡처에 비밀값이 남지 않게 하려는 것이다.

실행
  ./.venv/Scripts/python.exe tools/check_keys.py
  ./.venv/Scripts/python.exe tools/check_keys.py --live   # 실제 API 1회 호출까지
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

KEYS = [
    ("ANTHROPIC_API_KEY", "sk-ant-", "리포트 문장 생성 (런타임 필수)"),
    ("KASI_SERVICE_KEY", "", "절기 대조 (검증 스크립트에서만)"),
    ("SUPABASE_URL", "https://", "DB (7단계 이후)"),
    ("SUPABASE_SERVICE_ROLE_KEY", "", "DB 서버 전용 (7단계 이후)"),
]


def mask(value: str) -> str:
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:12]}{'*' * 8} (총 {len(value)}자)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="Anthropic API 실제 호출 1회")
    args = ap.parse_args()

    load_dotenv(ENV_PATH, override=False)
    print(f"읽은 파일: {ENV_PATH} {'(있음)' if ENV_PATH.exists() else '(없음)'}")
    print()

    ok = True
    for name, prefix, purpose in KEYS:
        raw = os.environ.get(name, "").strip()
        if not raw or raw == "CHANGE_ME":
            print(f"  ✗ {name:32} 없음        — {purpose}")
            if name == "ANTHROPIC_API_KEY":
                ok = False
            continue
        shape = "" if not prefix else ("" if raw.startswith(prefix) else f"  ⚠️ {prefix} 로 시작해야 합니다")
        print(f"  ✓ {name:32} {mask(raw)}{shape}")

    if not args.live:
        print()
        print("실제 호출까지 확인하려면:  --live 옵션을 붙여 다시 실행")
        return 0 if ok else 1

    print()
    if not ok:
        print("ANTHROPIC_API_KEY 가 없어 호출을 건너뜁니다.")
        return 1

    print("Anthropic API 호출 중…")
    try:
        import anthropic
    except ImportError:
        print("  anthropic 패키지가 없습니다:  pip install anthropic")
        return 1

    try:
        client = anthropic.Anthropic()
        res = client.messages.create(
            model="claude-opus-5",
            max_tokens=16,
            messages=[{"role": "user", "content": "'준비됨' 이라고만 답하세요."}],
        )
        text = next((b.text for b in res.content if b.type == "text"), "")
        print(f"  ✓ 응답: {text.strip()!r}")
        print(f"  ✓ 토큰: 입력 {res.usage.input_tokens} / 출력 {res.usage.output_tokens}")
        print(f"  ✓ 모델: {res.model}")
        return 0
    except anthropic.AuthenticationError:
        print("  ✗ 인증 실패 — 키가 잘못되었거나 폐기되었습니다.")
    except anthropic.PermissionDeniedError:
        print("  ✗ 권한 없음 — 크레딧 충전 여부와 워크스페이스 권한을 확인하세요.")
    except anthropic.RateLimitError:
        print("  ✗ 레이트리밋 — 키는 유효합니다. 잠시 후 다시 시도하세요.")
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ 실패: {type(e).__name__}: {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
