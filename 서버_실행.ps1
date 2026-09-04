# 청단사주타로 — 내 PC 를 서버로 (PRD §14.6)
#
# 화면과 API 를 한 서버가 함께 내보낸다. 주소가 하나라 터널링이 단순하다.
#
# 실행:  PowerShell 에서  .\서버_실행.ps1
#        공개까지 한 번에:  .\서버_실행.ps1 -공개

param(
    [switch]$공개,          # Cloudflare 터널로 인터넷에 공개
    [int]$포트 = 8000
)

$ErrorActionPreference = "Stop"
$루트 = $PSScriptRoot
$파이썬 = Join-Path $루트 "backend\.venv\Scripts\python.exe"

Write-Host ""
Write-Host "청단사주타로 서버" -ForegroundColor Yellow
Write-Host "────────────────────────────────────" -ForegroundColor DarkGray

# ── 1. 준비 확인 ───────────────────────────────────────────
if (-not (Test-Path $파이썬)) {
    Write-Host "✗ 파이썬 환경이 없습니다. 먼저 아래를 실행하세요:" -ForegroundColor Red
    Write-Host "    cd backend"
    Write-Host "    python -m venv .venv"
    Write-Host "    .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

$키파일 = Join-Path $루트 "backend\.env"
if (-not (Test-Path $키파일)) {
    Write-Host "! backend\.env 가 없습니다 — 문장 생성 없이 계산 결과만 나옵니다." -ForegroundColor DarkYellow
}

# ── 2. 화면 빌드 ───────────────────────────────────────────
$dist = Join-Path $루트 "frontend\dist"
Write-Host "화면을 빌드합니다..." -ForegroundColor Gray
Push-Location (Join-Path $루트 "frontend")
try {
    if (-not (Test-Path "node_modules")) { npm install | Out-Null }
    npm run build | Out-Null
} finally {
    Pop-Location
}
if (-not (Test-Path $dist)) {
    Write-Host "✗ 화면 빌드에 실패했습니다." -ForegroundColor Red
    exit 1
}
Write-Host "✓ 화면 준비 완료" -ForegroundColor Green

# ── 3. 서버 기동 ───────────────────────────────────────────
# 0.0.0.0 으로 열어 같은 공유기 안의 다른 기기(휴대폰)에서도 볼 수 있게 한다.
$env:APP_ENV = "production"     # 운영 모드 — /docs 를 닫는다

Write-Host ""
Write-Host "내 PC 에서      : http://localhost:$포트" -ForegroundColor Cyan
$내주소 = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1).IPAddress
if ($내주소) {
    Write-Host "같은 와이파이서 : http://${내주소}:$포트  (휴대폰에서 열어보세요)" -ForegroundColor Cyan
}

if ($공개) {
    Write-Host ""
    Write-Host "인터넷 공개 주소를 만드는 중... (cloudflared 필요)" -ForegroundColor Gray
    if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
        Write-Host "✗ cloudflared 가 없습니다. 설치:" -ForegroundColor Red
        Write-Host "    winget install --id Cloudflare.cloudflared"
        Write-Host "  설치 후 다시 실행하세요."
        exit 1
    }
    Start-Process cloudflared -ArgumentList "tunnel --url http://localhost:$포트" -NoNewWindow
    Write-Host "  터널 창에 뜨는 https://....trycloudflare.com 주소를 손님에게 보내세요." -ForegroundColor Gray
}

Write-Host ""
Write-Host "종료하려면 Ctrl+C" -ForegroundColor DarkGray
Write-Host "────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

& $파이썬 -m uvicorn app.main:app --host 0.0.0.0 --port $포트 --app-dir (Join-Path $루트 "backend")
