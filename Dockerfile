# 청단사주타로 — 클라우드 배포 이미지 (PRD §14.6 단일 오리진)
#
# 화면과 API 를 한 서버가 함께 내보낸다. 로컬의 서버_실행.ps1 과 같은 구조라
# 주소가 하나이고 CORS 가 필요 없다.

# ── 1단계: 화면 빌드 ────────────────────────────────────────
FROM node:22-alpine AS web
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# 목업을 반드시 끈다. readings.ts 의 기본값이 "목업 켬" 이라,
# 이 한 줄이 없으면 배포본이 가짜 리포트를 보여준다.
ENV VITE_USE_MOCK=false
# VITE_API_BASE_URL 은 비워 둔다 — 비어 있으면 같은 서버의 /api/v1 을 쓴다.

RUN npm run build && npm run check:secrets

# ── 2단계: 실행 ─────────────────────────────────────────────
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

# main.py 는 자기 위치 기준 parents[2]/frontend/dist 에서 화면을 찾는다.
# 로컬과 같은 폴더 모양을 유지해야 화면이 서빙된다.
COPY --from=web /build/dist frontend/dist

# 루트로 돌리지 않는다. /var/data 는 영구 디스크를 붙일 자리(render.yaml 참고).
RUN useradd -m -u 10001 saju \
    && mkdir -p /var/data /app/backend/data \
    && chown -R saju:saju /var/data /app
USER saju

ENV APP_ENV=production PORT=8000
EXPOSE 8000

# 플랫폼이 넘겨주는 $PORT 를 그대로 쓴다 (Render 는 10000 을 준다).
CMD ["sh", "-c", "python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
