# 세권사주타로 — 상시 실행 (가입 없이 쓰는 방식)
#
# 서버와 터널을 띄우고, 터널이 끊기면 자동으로 다시 연결한다.
# 지금 주소는 항상 현재주소.txt 에 적어 둔다.
#
# 실행:  .\상시실행.ps1
# 종료:  이 창에서 Ctrl+C
#
# ── 알아두실 것 ──────────────────────────────────────────
#  · 이 창을 닫으면 서비스도 멈춥니다. 켜 두세요.
#  · PC 를 끄거나 절전에 들어가면 멈춥니다. 절전을 꺼 두세요.
#  · 무료 터널이라 다시 연결될 때마다 주소가 바뀝니다.
#    바뀌면 이 창과 현재주소.txt 에 새 주소가 나옵니다.

param(
    [int]$포트 = 8000
)

$ErrorActionPreference = "Stop"
$루트 = $PSScriptRoot
$파이썬 = Join-Path $루트 "backend\.venv\Scripts\python.exe"
$주소파일 = Join-Path $루트 "현재주소.txt"
$터널로그 = Join-Path $env:TEMP "saju-tunnel.log"

function 알림($글, $색 = "Gray") { Write-Host "  $글" -ForegroundColor $색 }

Write-Host ""
Write-Host "세권사주타로 — 상시 실행" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

# ── 준비 확인 ────────────────────────────────────────────
if (-not (Test-Path $파이썬)) {
    알림 "✗ 파이썬 환경이 없습니다. backend 에서 .venv 를 먼저 만드세요." Red
    exit 1
}
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    알림 "✗ cloudflared 가 없습니다. 설치:" Red
    알림 "    winget install --id Cloudflare.cloudflared"
    exit 1
}

# ── 화면 빌드 ────────────────────────────────────────────
$dist = Join-Path $루트 "frontend\dist"
if (-not (Test-Path $dist)) {
    알림 "화면을 빌드합니다... (처음 한 번만 오래 걸립니다)"
    Push-Location (Join-Path $루트 "frontend")
    try {
        if (-not (Test-Path "node_modules")) { npm install | Out-Null }
        $env:VITE_USE_MOCK = "false"      # 이걸 안 끄면 가짜 리포트가 나간다
        npm run build | Out-Null
    } finally { Pop-Location }
}
알림 "✓ 화면 준비 완료" Green

# ── 서버 기동 ────────────────────────────────────────────
# APP_ENV=production 이어야 /docs 와 /openapi.json 이 닫힌다.
$env:APP_ENV = "production"
$서버 = Start-Process $파이썬 `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$포트", `
                  "--app-dir", (Join-Path $루트 "backend") `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 3
알림 "✓ 서버 기동  (내 PC: http://localhost:$포트)" Green

$내주소 = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1).IPAddress
if ($내주소) { 알림 "  같은 와이파이 : http://${내주소}:$포트" Cyan }

# ── 터널 감시 반복 ───────────────────────────────────────
#  터널이 죽으면 다시 띄운다. 주소가 바뀌므로 그때마다 알려 준다.
$이전주소 = ""
$연결횟수 = 0

try {
    while ($true) {
        $연결횟수++
        Remove-Item $터널로그 -ErrorAction SilentlyContinue

        $터널 = Start-Process cloudflared `
            -ArgumentList "tunnel", "--url", "http://localhost:$포트" `
            -PassThru -NoNewWindow -RedirectStandardError $터널로그

        # 주소가 로그에 뜰 때까지 기다린다 (최대 60초)
        $주소 = ""
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 2
            if (Test-Path $터널로그) {
                $찾음 = Select-String -Path $터널로그 -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" `
                        -AllMatches -ErrorAction SilentlyContinue
                if ($찾음) { $주소 = $찾음.Matches[0].Value; break }
            }
            if ($터널.HasExited) { break }
        }

        if ($주소) {
            $주소 | Set-Content -Path $주소파일 -Encoding UTF8
            Write-Host ""
            Write-Host "  ════════════════════════════════════════════════" -ForegroundColor DarkGray
            if ($연결횟수 -gt 1 -and $주소 -ne $이전주소) {
                Write-Host "   주소가 바뀌었습니다 (터널 재연결 $연결횟수 회차)" -ForegroundColor Yellow
            }
            Write-Host "   $주소" -ForegroundColor Green
            Write-Host "  ════════════════════════════════════════════════" -ForegroundColor DarkGray
            알림 "이 주소는 현재주소.txt 에도 적어 뒀습니다."
            알림 "끄려면 Ctrl+C. 이 창을 닫으면 서비스가 멈춥니다."
            Write-Host ""
            $이전주소 = $주소
        } else {
            알림 "! 터널 주소를 받지 못했습니다. 10초 뒤 다시 시도합니다." Yellow
        }

        # 터널이 죽을 때까지 기다린다
        $터널.WaitForExit()
        알림 "터널 연결이 끊겼습니다. 다시 연결합니다..." Yellow
        Start-Sleep -Seconds 10
    }
}
finally {
    알림 "정리 중..." DarkGray
    if ($터널 -and -not $터널.HasExited) { Stop-Process -Id $터널.Id -Force -ErrorAction SilentlyContinue }
    if ($서버 -and -not $서버.HasExited) { Stop-Process -Id $서버.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item $주소파일 -ErrorAction SilentlyContinue
    알림 "종료했습니다. 데이터는 그대로 남아 있습니다." DarkGray
}
