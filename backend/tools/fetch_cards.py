"""타로 카드 이미지 받아오기 (PRD §18.1 Q5).

라이더-웨이트 1909년판 **퍼블릭 도메인** 스캔본을 위키미디어 공용에서 받아
frontend/public/cards/ 에 저장한다. 현대 리메이크판·앱 이미지는 저작권이
살아 있으므로 절대 쓰지 않는다.

  원화: Pamela Colman Smith (1878~1951) · 1909년 발행
  사후 70년(2021년) 경과 + 1909년 발행으로 퍼블릭 도메인

한 번만 실행하면 되고, 받은 파일은 저장소에 커밋한다(외부 의존 제거).

실행
  ./.venv/Scripts/python.exe tools/fetch_cards.py
  ./.venv/Scripts/python.exe tools/fetch_cards.py --force   # 이미 있어도 다시 받기
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tarot_service import DECK  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "cards"
BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/"
WIDTH = 500

# 위키미디어는 설명이 있는 User-Agent 를 요구한다. 없으면 429/403 이 난다.
UA = "saju-tarot-asset-fetch/1.0 (public-domain RWS deck; contact: local dev)"

_MAJOR_FILES = {
    "The Fool": "RWS_Tarot_00_Fool.jpg",
    "The Magician": "RWS_Tarot_01_Magician.jpg",
    "The High Priestess": "RWS_Tarot_02_High_Priestess.jpg",
    "The Empress": "RWS_Tarot_03_Empress.jpg",
    "The Emperor": "RWS_Tarot_04_Emperor.jpg",
    "The Hierophant": "RWS_Tarot_05_Hierophant.jpg",
    "The Lovers": "RWS_Tarot_06_Lovers.jpg",
    "The Chariot": "RWS_Tarot_07_Chariot.jpg",
    "Strength": "RWS_Tarot_08_Strength.jpg",
    "The Hermit": "RWS_Tarot_09_Hermit.jpg",
    "Wheel of Fortune": "RWS_Tarot_10_Wheel_of_Fortune.jpg",
    "Justice": "RWS_Tarot_11_Justice.jpg",
    "The Hanged Man": "RWS_Tarot_12_Hanged_Man.jpg",
    "Death": "RWS_Tarot_13_Death.jpg",
    "Temperance": "RWS_Tarot_14_Temperance.jpg",
    "The Devil": "RWS_Tarot_15_Devil.jpg",
    "The Tower": "RWS_Tarot_16_Tower.jpg",
    "The Star": "RWS_Tarot_17_Star.jpg",
    "The Moon": "RWS_Tarot_18_Moon.jpg",
    "The Sun": "RWS_Tarot_19_Sun.jpg",
    "Judgement": "RWS_Tarot_20_Judgement.jpg",
    "The World": "RWS_Tarot_21_World.jpg",
}

_SUIT_DIR = {"Wands": "Wands", "Cups": "Cups", "Swords": "Swords", "Pentacles": "Pents"}
_RANK_NUM = {
    "Ace": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7,
    "Eight": 8, "Nine": 9, "Ten": 10, "Page": 11, "Knight": 12, "Queen": 13, "King": 14,
}


def slug(name: str) -> str:
    """'Eight of Pentacles' → 'eight-of-pentacles' (프론트에서 쓰는 파일명)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def commons_filename(card_name: str) -> str | None:
    if card_name in _MAJOR_FILES:
        return _MAJOR_FILES[card_name]
    m = re.match(r"^(\w+) of (\w+)$", card_name)
    if not m:
        return None
    rank, suit = m.group(1), m.group(2)
    if rank not in _RANK_NUM or suit not in _SUIT_DIR:
        return None
    return f"{_SUIT_DIR[suit]}{_RANK_NUM[rank]:02d}.jpg"


def download(filename: str, dest: Path, tries: int = 4) -> tuple[bool, str]:
    url = f"{BASE}{urllib.parse.quote(filename)}?width={WIDTH}"
    delay = 2.0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                data = res.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < tries:
                time.sleep(delay)
                delay *= 2
                continue
            return False, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            if attempt < tries:
                time.sleep(delay)
                delay *= 2
                continue
            return False, type(e).__name__

        # 오류 페이지를 이미지로 저장하지 않는다
        if len(data) < 10_000 or not data.startswith(b"\xff\xd8"):
            if attempt < tries:
                time.sleep(delay)
                delay *= 2
                continue
            return False, f"이미지 아님 ({len(data)}바이트)"

        dest.write_bytes(data)
        return True, f"{len(data) // 1024}KB"
    return False, "재시도 초과"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=1.2, help="요청 간 간격(초)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, str]] = []
    got = skipped = 0

    for card in DECK:
        filename = commons_filename(card.name)
        if filename is None:
            failures.append((card.name, "파일명 규칙에 없음"))
            continue
        dest = OUT_DIR / f"{slug(card.name)}.jpg"
        if dest.exists() and not args.force:
            skipped += 1
            continue

        ok, info = download(filename, dest)
        if ok:
            got += 1
            print(f"  ✓ {card.name_ko:14} {dest.name:26} {info}")
        else:
            failures.append((card.name, info))
            print(f"  ✗ {card.name_ko:14} {filename:26} {info}")
        time.sleep(args.delay)

    print()
    print(f"받음 {got} · 건너뜀 {skipped} · 실패 {len(failures)} → {OUT_DIR}")
    if failures:
        print("실패 목록:")
        for name, why in failures:
            print(f"  {name}: {why}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
