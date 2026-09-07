# 세권사주타로 — 자동 백업 (작업 스케줄러 전용)
#
# 손으로 돌리는 것은 백업.ps1 이다. 이 파일은 **무인 실행** 전용이고,
# 차이는 하나뿐 — 암호를 물어보지 않고 저장해 둔 것을 꺼내 쓴다.
#
# 암호는 윈도우 DPAPI 로 봉해 둔다. 같은 사용자·같은 PC 에서만 풀리고,
# 파일을 훔쳐가도 다른 컴퓨터에서는 열리지 않는다. 저장소 밖(LOCALAPPDATA)에
# 두므로 실수로 커밋될 일도 없다.
#
# ⚠️ 그래도 암호가 이 PC 에 있다는 것은 PRD §12.17 의 "암호를 이 컴퓨터에
#    저장하지 말라"와 어긋난다. 그 규칙의 이유는 **필드 암호화 키가 백업 안에
#    함께 들어가서** 암호 하나가 전부를 지키는 단일 비밀이 되기 때문이다.
#    그래서 자동 백업은 --키제외 로 돈다 — 키를 백업에 넣지 않는다.
#    암호가 새더라도 그것만으로는 이름·생년월일이 열리지 않는다.
#
#    대신 **필드 키를 따로 한 번 보관해야 한다.** 안 하면 백업이 있어도
#    개인정보를 복호화할 수 없다:  backend\data\field_key.txt
#
#   처음 한 번만   .\자동백업.ps1 -암호설정      ← 암호를 직접 입력
#   스케줄러 등록  .\자동백업.ps1 -등록
#   지금 시험      .\자동백업.ps1 -지금
#   상태 확인      .\자동백업.ps1 -상태
#   등록 해제      .\자동백업.ps1 -해제

param(
    [switch]$암호설정,
    [switch]$등록,
    [switch]$해제,
    [switch]$상태,
    [switch]$지금
)

$ErrorActionPreference = "Stop"
$루트 = $PSScriptRoot
$작업이름 = "세권사주타로 백업"
$금고 = Join-Path $env:LOCALAPPDATA "saju_tarot\backup-passphrase.xml"
$로그 = Join-Path $env:LOCALAPPDATA "saju_tarot\backup.log"
$오프사이트 = Join-Path $env:USERPROFILE "OneDrive\saju-backups"

function 적기($글, $색 = "Gray") {
    $줄 = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $글
    New-Item -ItemType Directory -Force -Path (Split-Path $로그) | Out-Null
    Add-Content -Path $로그 -Value $줄 -Encoding utf8
    Write-Host $글 -ForegroundColor $색
}

# ── 암호 저장 (사람이 직접 입력한다) ─────────────────────────
if ($암호설정) {
    Write-Host ""
    Write-Host "백업 암호를 저장합니다." -ForegroundColor Yellow
    Write-Host "기존 백업과 **같은 암호**를 넣으세요. 다르면 옛 사본을 못 엽니다." -ForegroundColor DarkYellow
    Write-Host ""
    $암호 = Read-Host "  백업 암호" -AsSecureString
    if ($암호.Length -eq 0) { Write-Host "  비어 있습니다." -ForegroundColor Red; exit 1 }

    New-Item -ItemType Directory -Force -Path (Split-Path $금고) | Out-Null
    $암호 | ConvertFrom-SecureString | Set-Content -Path $금고 -Encoding utf8
    Write-Host ""
    Write-Host "  저장했습니다: $금고" -ForegroundColor Green
    Write-Host "  이 파일은 이 PC·이 사용자만 풀 수 있습니다." -ForegroundColor DarkGray
    exit 0
}

# ── 스케줄러 등록 / 해제 / 상태 ──────────────────────────────
if ($등록) {
    if (-not (Test-Path $금고)) {
        Write-Host "  암호를 먼저 저장하세요:  .\자동백업.ps1 -암호설정" -ForegroundColor Red
        exit 1
    }
    # 자동 백업은 키를 넣지 않는다. 키가 어디에도 없으면 백업이 무용지물이므로
    # 등록 전에 사람에게 한 번 확인받는다.
    $키파일 = Join-Path $루트 "backend\data\field_key.txt"
    Write-Host ""
    Write-Host "자동 백업은 필드 암호화 키를 백업에 넣지 않습니다 (--키제외)." -ForegroundColor Yellow
    Write-Host "그래서 이 파일을 비밀번호 관리자에 **한 번** 보관해 두셔야 합니다:" -ForegroundColor Yellow
    Write-Host "  $키파일" -ForegroundColor Cyan
    Write-Host "보관하지 않으면 백업이 있어도 이름·생년월일을 복호화할 수 없습니다." -ForegroundColor DarkYellow
    Write-Host ""
    $답 = Read-Host "  보관을 마쳤습니까? (예 를 입력)"
    if ($답 -ne "예") {
        Write-Host "  등록을 멈췄습니다. 키를 먼저 보관하세요." -ForegroundColor Red
        exit 1
    }

    $동작 = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -지금" `
        -WorkingDirectory $루트
    # 매일 21시. 그 시간에 PC 가 꺼져 있었다면 켜진 뒤에 따라 돈다.
    $방아쇠 = New-ScheduledTaskTrigger -Daily -At 21:00
    $설정 = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

    Register-ScheduledTask -TaskName $작업이름 -Action $동작 -Trigger $방아쇠 `
        -Settings $설정 -Description "리포트 DB 를 암호화해 백업하고 OneDrive 로 사본을 보낸다 (PRD 12.17)" `
        -Force | Out-Null
    적기 "스케줄러 등록: 매일 21:00" "Green"
    exit 0
}

if ($해제) {
    Unregister-ScheduledTask -TaskName $작업이름 -Confirm:$false
    적기 "스케줄러 해제" "Yellow"
    exit 0
}

if ($상태) {
    Write-Host ""
    Write-Host "자동 백업 상태" -ForegroundColor Yellow
    Write-Host "────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ("  암호 저장     : " + $(if (Test-Path $금고) { "됨" } else { "안 됨 — -암호설정 먼저" }))
    $작업 = Get-ScheduledTask -TaskName $작업이름 -ErrorAction SilentlyContinue
    if ($작업) {
        $정보 = Get-ScheduledTaskInfo -TaskName $작업이름
        Write-Host ("  스케줄러      : " + $작업.State)
        Write-Host ("  마지막 실행   : " + $정보.LastRunTime + "  (결과 " + $정보.LastTaskResult + ")")
        Write-Host ("  다음 실행     : " + $정보.NextRunTime)
    } else {
        Write-Host "  스케줄러      : 등록 안 됨 — -등록 하세요"
    }
    $사본 = Get-ChildItem (Join-Path $루트 "backups") -Filter "saju-*.saju.enc" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending
    Write-Host ("  로컬 사본     : " + $사본.Count + "개" + $(if ($사본) { "  (최신 " + $사본[0].LastWriteTime + ")" }))
    $밖 = Get-ChildItem $오프사이트 -Filter "saju-*.saju.enc" -ErrorAction SilentlyContinue
    Write-Host ("  OneDrive 사본 : " + $밖.Count + "개")
    $키파일 = Join-Path $루트 "backend\data\field_key.txt"
    Write-Host ("  필드 키 파일  : " + $(if (Test-Path $키파일) { "있음 — 비밀번호 관리자에도 보관 필요" } else { "없음 (환경변수 구성)" }))
    Write-Host ("  로그           : " + $로그) -ForegroundColor DarkGray
    Write-Host ""
    exit 0
}

# ── 실제 백업 (스케줄러가 이걸 부른다) ───────────────────────
if (-not $지금) {
    Write-Host "쓸 방법:  -암호설정 | -등록 | -지금 | -상태 | -해제" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $금고)) {
    적기 "실패 — 암호가 저장돼 있지 않다 (-암호설정)" "Red"
    exit 1
}

$파이썬 = Join-Path $루트 "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $파이썬)) { 적기 "실패 — .venv 가 없다" "Red"; exit 1 }

try {
    # DPAPI 봉인을 풀어 환경변수로만 넘긴다. 디스크에 평문으로 쓰지 않는다.
    $보안문자열 = Get-Content $금고 | ConvertTo-SecureString
    $env:BACKUP_PASSPHRASE = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($보안문자열))

    Push-Location (Join-Path $루트 "backend")
    try {
        $출력 = & $파이썬 "tools\backup.py" "--키제외" 2>&1
        $성공 = $LASTEXITCODE -eq 0
    } finally { Pop-Location }

    if (-not $성공) {
        적기 "백업 실패 — $($출력 -join ' / ')" "Red"
        exit 1
    }

    # 오프사이트 사본 — 3-2-1 규칙의 "1벌은 다른 장소"
    $최신 = Get-ChildItem (Join-Path $루트 "backups") -Filter "saju-*.saju.enc" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($최신 -and (Test-Path (Split-Path $오프사이트))) {
        New-Item -ItemType Directory -Force -Path $오프사이트 | Out-Null
        Copy-Item $최신.FullName -Destination $오프사이트 -Force
        # 오프사이트도 같은 기간만 보관한다
        Get-ChildItem $오프사이트 -Filter "saju-*.saju.enc" |
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-28) } |
            Remove-Item -Force
        적기 "백업 완료 — $($최신.Name)  (OneDrive 사본 포함)" "Green"
    } else {
        적기 "백업 완료 — $($최신.Name)  (오프사이트는 건너뜀: OneDrive 없음)" "Yellow"
    }
} catch {
    적기 "백업 실패 — $($_.Exception.Message)" "Red"
    exit 1
} finally {
    # 환경변수는 이 프로세스에만 있었지만 명시적으로 지운다
    Remove-Item Env:BACKUP_PASSPHRASE -ErrorAction SilentlyContinue
}

# 로그가 무한히 자라지 않게 뒤쪽 2000줄만 남긴다
if ((Test-Path $로그) -and (Get-Content $로그).Count -gt 2000) {
    Get-Content $로그 -Tail 2000 | Set-Content $로그 -Encoding utf8
}
