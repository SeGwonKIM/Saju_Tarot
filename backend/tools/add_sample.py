"""말투 샘플을 명령 한 줄로 넣고 빼는 도구 (PRD §11.5 · Q7).

메모장으로 직접 고치다가 인코딩이 어긋나 파일이 통째로 무시되는 사고를 막는다.
파일은 항상 UTF-8(BOM 없음)로 저장한다.

사용법
  # 넣기 (주제 있음)
  python tools/add_sample.py add 재회운 "지금 먼저 연락하시는 건 권하지 않습니다."

  # 넣기 (주제 없이)
  python tools/add_sample.py add - "마지막으로 한 말씀 드리면, 조급함이 제일 큰 적입니다."

  # 지금까지 넣은 것 보기
  python tools/add_sample.py list

  # 번호로 지우기
  python tools/add_sample.py remove 3

  # 예시 5건을 지우고 처음부터 다시 (내 문장만 남기고 싶을 때)
  python tools/add_sample.py clear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tone_samples import (  # noqa: E402
    MIN_SAMPLES,
    SAMPLES_PATH,
    ToneSample,
    parse,
)

TOPICS = ("재회운", "상대방속마음", "연애", "재물", "대인관계")
HEADER = "# 내 상담 말투 샘플\n"


def read_samples() -> list[ToneSample]:
    if not SAMPLES_PATH.exists():
        return []
    try:
        return parse(SAMPLES_PATH.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        print("⚠️ 기존 파일이 UTF-8 이 아닙니다. 내용을 읽을 수 없어 빈 목록에서 시작합니다.")
        print("   (기존 파일을 백업하려면 지금 중단하고 파일을 다른 곳에 복사해 두세요)")
        return []


def write_samples(samples: list[ToneSample]) -> None:
    lines = [HEADER]
    for i, s in enumerate(samples, 1):
        lines.append(f"\n## 사례 {i}\n")
        if s.topic:
            lines.append(f"주제: {s.topic}\n")
        lines.append(f"문장: {s.text}\n")
    SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES_PATH.write_text("".join(lines), encoding="utf-8", newline="\n")


def show(samples: list[ToneSample]) -> None:
    if not samples:
        print("아직 넣은 문장이 없습니다.")
    for i, s in enumerate(samples, 1):
        topic = s.topic or "(주제 없음)"
        print(f"  {i:2}. [{topic}] {s.text}")

    print()
    n = len(samples)
    if n >= MIN_SAMPLES:
        print(f"총 {n}건 — ✅ 적용됩니다 (서버를 다시 켜면 반영)")
    else:
        print(f"총 {n}건 — ⏳ {MIN_SAMPLES - n}건 더 넣으면 적용됩니다")

    by_topic: dict[str, int] = {}
    for s in samples:
        by_topic[s.topic or "(주제 없음)"] = by_topic.get(s.topic or "(주제 없음)", 0) + 1
    if by_topic:
        print("주제별: " + " · ".join(f"{k} {v}건" for k, v in by_topic.items()))
    missing = [t for t in TOPICS if t not in by_topic]
    if missing:
        print(f"아직 없는 주제: {' · '.join(missing)}  ← 넣으면 그 주제 어조가 더 정확해집니다")


def main() -> int:
    ap = argparse.ArgumentParser(description="상담 말투 샘플 관리")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="문장 하나 넣기")
    p_add.add_argument("topic", help=f"{' | '.join(TOPICS)} 또는 - (주제 없음)")
    p_add.add_argument("text", help="실제로 손님에게 보낸 문장")

    sub.add_parser("list", help="넣은 문장 보기")

    p_rm = sub.add_parser("remove", help="번호로 지우기")
    p_rm.add_argument("index", type=int)

    sub.add_parser("clear", help="전부 지우기")

    args = ap.parse_args()
    samples = read_samples()

    if args.cmd == "list":
        show(samples)
        return 0

    if args.cmd == "clear":
        write_samples([])
        print(f"전부 지웠습니다 → {SAMPLES_PATH}")
        return 0

    if args.cmd == "remove":
        if not 1 <= args.index <= len(samples):
            print(f"1 ~ {len(samples)} 사이 번호를 넣으세요.")
            return 1
        removed = samples.pop(args.index - 1)
        write_samples(samples)
        print(f"지웠습니다: {removed.text[:40]}")
        print()
        show(samples)
        return 0

    # add
    topic = None if args.topic == "-" else args.topic
    if topic is not None and topic not in TOPICS:
        print(f"주제는 {' | '.join(TOPICS)} 또는 - 여야 합니다. 받은 값: {topic}")
        return 1

    text = args.text.strip()
    if not text:
        print("문장이 비어 있습니다.")
        return 1
    if any(s.text == text for s in samples):
        print("이미 같은 문장이 있습니다.")
        return 1

    samples.append(ToneSample(topic=topic, text=text))
    write_samples(samples)
    print(f"넣었습니다 → {SAMPLES_PATH}")
    print()
    show(samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
