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

# 휴대폰에서 열 수 있는 **진짜** 랜 주소를 고른다. (서버_실행.ps1 과 같은 규칙)
#
# 예전에는 127.* 과 169.254.* 만 걸러내고 맨 위 것을 집었는데, WSL·Hyper-V 가
# 깔려 있으면 가상 어댑터(172.25.144.1 등)가 먼저 나온다. 그 주소는 휴대폰에서
# 절대 안 열린다 — 실제로 그렇게 안내하고 있었다.
#
# 그래서 **기본 경로(인터넷으로 나가는 길)를 가진 어댑터**의 주소를 쓴다.
function 내랜주소 {
    $경로 = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
            Sort-Object RouteMetric | Select-Object -First 1
    if ($경로) {
        $주소 = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $경로.ifIndex `
                 -ErrorAction SilentlyContinue |
                 Where-Object { $_.IPAddress -notlike "127.*" } |
                 Select-Object -First 1).IPAddress
        if ($주소) { return $주소 }
    }
    return (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and
            $_.InterfaceAlias -notlike "*vEthernet*" -and
            $_.InterfaceAlias -notlike "*Loopback*" -and
            $_.InterfaceAlias -notlike "*Bluetooth*"
        } | Select-Object -First 1).IPAddress
}

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

# **매번 빌드한다.** 예전에는 dist 가 없을 때만 빌드했는데, 그러면 화면 코드를
# 고쳐도 옛 dist 가 그대로 서비스된다. 실제로 사흘 지난 빌드가 공개되고 있었다
# — 개발 서버(:5173)에서는 고친 화면이 보여서 알아채지 못했다.
# 빌드는 3초면 끝나므로 조건을 걸어 아낄 값어치가 없다.
알림 "화면을 빌드합니다..."
Push-Location (Join-Path $루트 "frontend")
try {
    if (-not (Test-Path "node_modules")) { npm install | Out-Null }
    $env:VITE_USE_MOCK = "false"      # 이걸 안 끄면 가짜 리포트가 나간다
    npm run build | Out-Null
} finally { Pop-Location }

if (-not (Test-Path (Join-Path $dist "index.html"))) {
    알림 "✗ 화면 빌드에 실패했습니다." Red
    exit 1
}
알림 "✓ 화면 준비 완료" Green

# ── 서버 기동 ────────────────────────────────────────────
# APP_ENV=production 이어야 /docs 와 /openapi.json 이 닫힌다.
$env:APP_ENV = "production"
$서버 = Start-Process $파이썬 `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$포트", "--no-server-header", `
                  "--app-dir", (Join-Path $루트 "backend") `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 3
알림 "✓ 서버 기동  (내 PC: http://localhost:$포트)" Green

$내주소 = 내랜주소
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
