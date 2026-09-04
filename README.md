# 청단사주타로

이름·생년월일·출생시각·양력/음력을 입력하면 사주팔자와 타로를 결합해
**사주 풀이 · 이번 달 흐름 세 줄 · 주제별 조언**을 한 장으로 만들어 주는 웹서비스.

주제는 **재회운 · 상대방속마음 · 연애 · 재물 · 대인관계** 다섯 가지입니다.

- 만세력 기준 계산 — 절기·진태양시·역사적 표준시까지 보정
- 타로 3장 고정 스프레드 — 같은 사람·같은 달이면 항상 같은 카드
- 문장 생성은 LLM, **계산은 절대 LLM 에 맡기지 않습니다**
- 이름·생년월일은 암호화 저장, 90일 후 자동 삭제

- 설계 문서: [PRD](docs/PRD.md) — 화면·API·보안·검증까지
- 도메인 분석: [도메인분석](docs/도메인분석.md) — 왜 이렇게 만들었는지

## 구성

| 위치 | 스택 |
|---|---|
| `frontend/` | React 19 + Vite + TypeScript + Tailwind 4 |
| `backend/` | Python + FastAPI + SQLite |
| 만세력 | `lunar-python` + 한국 시간대 보정 레이어 (직접 구현) |
| 문장 생성 | OpenAI (공급자는 어댑터로 분리) |

## 내 PC 를 서버로 (PRD §14.6)

화면과 API 를 **한 서버가 함께** 내보냅니다. 주소가 하나라 CORS 문제가 없고 터널링이 단순합니다.

```powershell
cd C:\AI-Agent\saju_tarot
.\서버_실행.ps1              # 내 PC + 같은 와이파이 안에서 접속
.\서버_실행.ps1 -공개         # 인터넷에 공개 (Cloudflare 터널)
```

| 어디서 | 주소 |
|---|---|
| 내 PC | `http://localhost:8000` |
| 같은 와이파이 (휴대폰 등) | `http://<내 PC IP>:8000` — 실행하면 화면에 표시됩니다 |
| 인터넷 | `-공개` 옵션 실행 시 뜨는 `https://….trycloudflare.com` |

인터넷 공개에는 cloudflared 가 필요합니다: `winget install --id Cloudflare.cloudflared`

**공개 전 알아두실 것**
- 요청은 **IP당 시간당 10건, 전체 100건**으로 제한됩니다 (LLM 요금 보호)
- 운영 모드에서는 API 문서와 명세(`/openapi.json`)가 닫힙니다
- PC 를 끄거나 인터넷이 끊기면 서비스도 멈춥니다. 절전 모드도 해제해 두세요
- 무료 터널 주소는 **껐다 켜면 바뀝니다.** 고정 주소가 필요하면 Cloudflare 계정 + 도메인이 필요합니다

## 고정 주소로 배포 (Render)

내 PC 를 끄면 서비스가 멈추는 게 싫다면 클라우드에 올린다. 주소가 고정되고,
`main` 에 push 하면 자동으로 다시 배포된다.

`Dockerfile` 이 화면과 API 를 **한 이미지**로 묶는다 — 로컬의 `서버_실행.ps1`
과 같은 단일 오리진 구조다.

```bash
docker build -t saju-tarot .          # 로컬에서 먼저 확인하고 싶을 때
```

### 배포 절차

1. Render 대시보드 → **New → Blueprint** → 이 저장소 선택 (`render.yaml` 을 읽는다)
2. 아래 세 값을 Render 화면에서 직접 넣는다 — 저장소에는 남지 않는다

| 환경변수 | 없으면 |
|---|---|
| `OPENAI_API_KEY` | 서버는 뜨지만 문장 생성이 안 된다 (계산 결과만) |
| `FIELD_ENCRYPTION_KEY` | **재시작할 때마다 키가 새로 생겨 먼저 저장한 리포트를 못 읽는다** |
| `ADMIN_TOKEN` | 재시작할 때마다 상담자 토큰이 바뀐다 |

```bash
# FIELD_ENCRYPTION_KEY
python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
# ADMIN_TOKEN
python -c "import secrets;print(secrets.token_urlsafe(24))"
```

3. 배포 후 주소가 정해지면 `render.yaml` 의 `ALLOWED_ORIGINS` 를 그 주소로 바꾼다

### 알아둘 것

- **free 플랜에는 영구 디스크가 없다.** 재배포·재시작하면 SQLite 파일이 사라진다.
  리포트를 보관하려면 유료 플랜으로 올리고 `render.yaml` 의 `disk` 블록과
  `DB_PATH=/var/data/readings.db` 주석을 푼다
- free 플랜은 15분간 요청이 없으면 잠들고, 다음 접속이 느리다
- 말투 샘플(`backend/data/tone_samples.md`)은 실제 상담 문장이라 저장소에 없다.
  배포본은 few-shot 없이 일반 문체로 나간다 — 넣으려면 Render 의 Secret File 로 올린다
- 운영 모드라 `/docs` 와 `/openapi.json` 은 닫힌다

## 개발 환경 실행

```bash
# 백엔드 (http://localhost:8000)
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 프론트 (http://localhost:5173)
cd frontend
npm install
npm run dev
```

테스트: `cd backend && ./.venv/Scripts/python.exe -m pytest -q`
(실제 LLM 호출은 기본 제외 — 돌리려면 `pytest -m live`)

## 처음 한 번만 — 보안 설정 (PRD §12.11)

```bash
git config core.hooksPath .githooks    # 비밀값 커밋 차단 훅 활성화
cp .env.example backend/.env           # 값을 채운다. 이 파일은 커밋되지 않는다
cp .env.example frontend/.env          # VITE_ 로 시작하는 항목만 남긴다
```

### 손으로 해야 하는 단계 (웹에서)

- [ ] GitHub 저장소 → Settings → Code security → **Secret scanning** + **Push protection** 켜기
- [ ] GitHub · Render · Cloudflare · Supabase · Anthropic **전 계정 2FA** 켜기
- [ ] 복구 코드는 오프라인 보관

## 내 상담 말투 학습 (PRD §11.5)

문장 품질을 올리는 가장 큰 항목입니다. 규칙만으로는 모델이 일반론을 씁니다.

**방법 1 — 명령으로 넣기 (권장, 인코딩 사고 없음)**

```bash
cd backend
.\.venv\Scripts\python.exe toolsdd_sample.py add 재회운 "지금 먼저 연락하시는 건 권하지 않습니다."
.\.venv\Scripts\python.exe toolsdd_sample.py list      # 몇 건인지·적용됐는지 확인
.\.venv\Scripts\python.exe toolsdd_sample.py remove 3  # 번호로 삭제
.\.venv\Scripts\python.exe toolsdd_sample.py clear     # 예시 지우고 처음부터
```

주제는 `재회운 | 상대방속마음 | 연애 | 재물 | 대인관계` 또는 `-`(주제 없음).

**방법 2 — 파일 직접 편집**

`backend\data	one_samples.md` 를 열어 `## 사례 N` / `주제:` / `문장:` 세 줄씩 적습니다.
메모장에서 저장할 때 **인코딩을 UTF-8** 로 하세요(ANSI 로 저장하면 파일 전체가 무시됩니다).

**공통**
- 전체 합계 **5건 이상**이면 적용됩니다 (주제별 5건이 아닙니다)
- 이름·생년월일·연락처는 지우고 넣으세요 — 남아 있으면 그 문장을 버립니다
- 서버 재시작하면 반영되고 리포트의 "문체 학습 전 초안" 표시가 사라집니다

`tone_samples.md` 는 git 에 올라가지 않습니다. 개인정보로 보이는 문장은 로딩 시 걸러냅니다.

## 규칙

1. **비밀값은 코드에 없다.** 환경변수만. `VITE_` 접두사가 붙은 값은 브라우저에 공개된다 — 비밀값 금지.
2. **API 명세가 먼저다.** 기능이 바뀌면 코드보다 PRD §10을 먼저 고친다.
3. **수직 슬라이스.** 한 기능을 화면-API-저장까지 끝내고 테스트한 뒤 다음으로.
4. **매 단계 커밋.**
5. 키가 유출되면 **파일 삭제보다 키 폐기(revoke)가 먼저다.** → PRD §12.12 런북

## 진행 상황 (PRD §15)

- [x] 0단계 — 보안 바닥 (`.gitignore` · `.env.example` · pre-commit 훅)
- [x] 1단계 — 스캐폴드 + `/health` 연결 확인
- [x] 2단계 — 목업 데이터로 입력 폼·리포트 화면 완성
- [x] 3단계 — 음↔양 변환 API (`POST /calendar/convert`, `GET /calendar/lunar-year/{year}`)
- [x] 4단계 — 만세력 엔진 (한국 시간대 보정 + `lunar-python` 연결 + 불변식 테스트)
- [ ] 4b단계 — KASI 절기 전수 대조 (서비스 키 필요, 아래 참고)
- [x] 5단계 — `POST /readings` 실제 계산 연결 (목업 스위치 off)
- [x] 6단계 — 타로 엔진 + 카드 마스터 78장
- [x] 7단계 — 리포트 문장 생성 (OpenAI `gpt-5.5`, 어댑터로 분리)
- [x] 8단계 — 저장 (SQLite + 개인정보 암호화 + 자동 삭제)
- [x] 9단계 — 공유 링크
- [ ] 상담자 로그인 (혼자 쓰실 거면 불필요 — Q2)

## 데이터 파일

| 파일 | 내용 | 백업 |
|---|---|---|
| `backend/data/readings.db` | 저장된 리포트 (이름·생년월일은 암호화) | 주 1회 권장 |
| `backend/data/field_key.txt` | **암호화 키** — 잃으면 저장된 리포트를 못 읽습니다 | 별도 보관 필수 |
| `backend/data/tone_samples.md` | 내 상담 말투 샘플 | — |

셋 다 git 에 올라가지 않습니다. **DB 와 키를 같은 곳에 백업하지 마세요** — 한 번에 새면 암호화가 무의미해집니다.

## KASI 절기 대조 (4b단계)

라이브러리 절기 시각이 한국천문연구원 발표값과 분 단위로 맞는지 전 연도에 걸쳐 확인합니다.
공공데이터포털(data.go.kr)에서 '24절기 정보' 서비스 키를 받은 뒤:

```bash
cd backend && $env:KASI_SERVICE_KEY="발급받은키"; ./.venv/Scripts/python.exe tools/verify_solar_terms.py --from 1950 --to 2050
```

불일치 목록이 `tools/solar_term_diff.json` 에 저장됩니다.
