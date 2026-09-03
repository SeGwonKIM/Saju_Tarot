# 사주·타로 상담 리포트

이름·생년월일·출생시각·양력/음력을 입력하면 사주팔자와 타로를 결합해
**"이번 달 흐름 세 줄 + 연애·직업·재물 조언 한 줄씩"** 리포트를 만들어 주는 웹서비스.

- 설계 문서: [PRD](../제출자료/도매인역량/PRD_saju_tarot.md) v2.11
- 도메인 분석: [domain_breakdown](../제출자료/도매인역량/domain_breakdown.md) v2.11

## 구성

| 위치 | 스택 | 배포 예정지 |
|---|---|---|
| `frontend/` | React 19 + Vite + TypeScript + Tailwind 4 | Cloudflare Pages |
| `backend/` | Python + FastAPI | Render |
| (예정) | Supabase Postgres + Auth (RLS) | Supabase |

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
- [ ] 3단계 — 음↔양 변환 API
- [ ] 4단계 — 만세력 엔진 + 골든 테스트 100건
