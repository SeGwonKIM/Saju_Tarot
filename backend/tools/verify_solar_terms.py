"""KASI 절기 전수 대조 (PRD §16.1).

사람이 골든테스트 100건을 만드는 대신, 한국천문연구원(KASI) 24절기 API 와
라이브러리 계산값을 **연도 범위 전체**에 걸쳐 자동 대조한다.
1900~2050년이면 약 3,600건 — 커버리지가 36배 넓고 사람 손이 안 간다.

무엇을 확인하는가
  라이브러리는 절기를 베이징 기준으로 계산한다. 여기에 1시간을 더한 값이
  KASI 가 발표한 한국 기준 시각과 **분 단위로 일치**해야 한다.
  어긋나는 절기만 목록으로 뽑아 보정 테이블에 넣는다.

키를 넣는 곳 (둘 중 하나, PRD §12.1)
  ① backend/.env 에  KASI_SERVICE_KEY=발급받은키   ← 이 파일은 .gitignore 로 막혀 있다
  ② 셸 환경변수      $env:KASI_SERVICE_KEY="..."   ← 그 셸에서만 유효

실행
  python tools/verify_solar_terms.py --from 1950 --to 2050

키를 코드·저장소에 넣지 않는다. pre-commit 훅이 실수로 커밋되는 것도 막는다.
결과는 tools/solar_term_diff.json 에 저장된다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.saju_service import solar_term_table  # noqa: E402

KASI_URL = "https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/get24DivisionsInfo"
OUT_PATH = Path(__file__).parent / "solar_term_diff.json"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# KASI 응답의 절기 이름(한글) → 라이브러리 키(간체자). 라이브러리가 간체를 쓴다.
NAME_MAP = {
    "소한": "小寒", "대한": "大寒", "입춘": "立春", "우수": "雨水",
    "경칩": "惊蛰", "춘분": "春分", "청명": "清明", "곡우": "谷雨",
    "입하": "立夏", "소만": "小满", "망종": "芒种", "하지": "夏至",
    "소서": "小暑", "대서": "大暑", "입추": "立秋", "처서": "处暑",
    "백로": "白露", "추분": "秋分", "한로": "寒露", "상강": "霜降",
    "입동": "立冬", "소설": "小雪", "대설": "大雪", "동지": "冬至",
}


def fetch_kasi_month(year: int, month: int, key: str) -> dict[str, tuple[datetime, bool]]:
    """KASI 에서 그 달 절기를 가져온다.

    ⚠️ `solMonth` 는 **필수 파라미터**다(공식 문서 확인). 연 단위로 한 번 부르면 안 되고
       달마다 호출해야 한다.

    ⚠️ 공식 문서의 출력 항목에는 시각(`kst`)이 없고 날짜(`locdate`)만 있다.
       실제 응답에 kst 가 오는 경우가 있어 **있으면 쓰고 없으면 날짜만 비교**한다.
       돌려주는 bool 이 '시각까지 있었는지' 여부다.
    """
    params = urllib.parse.urlencode(
        {
            "serviceKey": key,
            "solYear": year,
            "solMonth": f"{month:02d}",
            "numOfRows": 10,
            "pageNo": 1,
        },
        safe="",
    )
    with urllib.request.urlopen(f"{KASI_URL}?{params}", timeout=20) as res:
        root = ElementTree.fromstring(res.read())

    code = root.findtext(".//resultCode")
    if code not in (None, "00", "0"):
        raise RuntimeError(f"KASI 오류 resultCode={code} {root.findtext('.//resultMsg')}")

    out: dict[str, tuple[datetime, bool]] = {}
    for item in root.iter("item"):
        name = (item.findtext("dateName") or "").strip()
        ymd = (item.findtext("locdate") or "").strip()
        if not (name and len(ymd) == 8):
            continue
        hm = (item.findtext("kst") or "").strip()
        has_time = len(hm) == 4 and hm.isdigit()
        out[name] = (
            datetime(
                int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]),
                int(hm[:2]) if has_time else 0,
                int(hm[2:]) if has_time else 0,
            ),
            has_time,
        )
    return out


def fetch_kasi_year(year: int, key: str) -> dict[str, tuple[datetime, bool]]:
    out: dict[str, tuple[datetime, bool]] = {}
    for month in range(1, 13):
        out.update(fetch_kasi_month(year, month, key))
    return out


def compare_year(year: int, key: str) -> tuple[list[dict[str, object]], int, int]:
    """(불일치 목록, 대조 건수, 시각까지 비교한 건수)"""
    kasi = fetch_kasi_year(year, key)
    lib = solar_term_table(year)
    diffs: list[dict[str, object]] = []
    compared = 0
    with_time = 0

    for ko_name, (kasi_time, has_time) in kasi.items():
        hanja = NAME_MAP.get(ko_name)
        if hanja is None:
            continue  # 절기 외 항목(잡절 등)이 섞여 오면 건너뛴다
        if hanja not in lib:
            diffs.append({"year": year, "term": ko_name, "issue": "라이브러리에 없는 절기"})
            continue

        lib_time = datetime.fromisoformat(lib[hanja])
        compared += 1

        if has_time:
            with_time += 1
            delta_min = round((lib_time - kasi_time).total_seconds() / 60)
            if delta_min != 0:
                diffs.append(
                    {
                        "year": year, "term": ko_name,
                        "kasi": kasi_time.isoformat(sep=" "),
                        "library": lib_time.isoformat(sep=" "),
                        "delta_minutes": delta_min,
                    }
                )
        elif lib_time.date() != kasi_time.date():
            # 시각이 없으면 날짜만 비교한다. 날짜가 다르면 그 날 출생자의 월주가 통째로 틀린다
            diffs.append(
                {
                    "year": year, "term": ko_name,
                    "kasi_date": kasi_time.date().isoformat(),
                    "library_date": lib_time.date().isoformat(),
                    "note": "KASI 응답에 시각이 없어 날짜만 비교",
                }
            )
    return diffs, compared, with_time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=1950)
    ap.add_argument("--to", dest="end", type=int, default=2050)
    args = ap.parse_args()

    # backend/.env 를 읽는다. 셸 환경변수가 이미 있으면 그쪽이 이긴다.
    load_dotenv(ENV_PATH, override=False)

    key = os.environ.get("KASI_SERVICE_KEY", "").strip()
    if not key or key == "CHANGE_ME":
        print("KASI_SERVICE_KEY 가 없습니다. 둘 중 하나로 넣으세요.")
        print()
        print(f"  ① 파일 (권장):  {ENV_PATH}")
        print("     KASI_SERVICE_KEY=발급받은키          ← 이 한 줄만 추가")
        print()
        print("  ② 이 셸에서만:  $env:KASI_SERVICE_KEY=\"발급받은키\"")
        print()
        print("공공데이터포털 → 한국천문연구원_특일 정보 → 활용신청(자동승인)")
        print("→ 마이페이지 → 개발계정 → 일반 인증키(Decoding) 값을 씁니다.")
        return 2

    all_diffs: list[dict[str, object]] = []
    checked = 0
    timed = 0
    years = range(args.start, args.end + 1)
    print(f"{len(years)}개 연도 × 12개월 = 요청 {len(years) * 12}건 (개발계정 한도 10,000건/일)")
    print()

    for year in years:
        try:
            diffs, compared, with_time = compare_year(year, key)
        except Exception as e:  # 네트워크·응답 형식 문제는 그 해만 건너뛴다
            print(f"  {year}: 조회 실패 ({type(e).__name__}: {e})")
            continue
        checked += compared
        timed += with_time
        all_diffs.extend(diffs)
        mark = "OK" if not diffs else f"차이 {len(diffs)}건"
        print(f"  {year}: 절기 {compared}개 대조 · {mark}")

    OUT_PATH.write_text(
        json.dumps(all_diffs, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print()
    print(f"대조 {checked}건 (시각까지 비교 {timed}건) · 불일치 {len(all_diffs)}건 → {OUT_PATH.name}")
    if checked and timed == 0:
        print("⚠️ KASI 응답에 시각(kst)이 없어 날짜만 대조했습니다.")
        print("   절기 경계 당일 출생자의 연·월주 검증에는 시각이 필요합니다 — PRD §16.1 후속 과제.")
    return 0 if not all_diffs else 1


if __name__ == "__main__":
    raise SystemExit(main())
