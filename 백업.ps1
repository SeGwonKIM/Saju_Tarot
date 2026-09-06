# 세권사주타로 — 리포트 DB 백업 (PRD §12.17)
#
# 실행:  .\백업.ps1                    백업 만들기
#        .\백업.ps1 -목록               백업 목록
#        .\백업.ps1 -검증 <파일>        진짜 열리는지 확인
#        .\백업.ps1 -복원 <파일>        복원 (덮어쓰지 않음)

param(
    [switch]$목록,
    [string]$검증,
    [string]$복원,
    [switch]$키제외          # 필드 암호화 키를 백업에 넣지 않는다
)

$ErrorActionPreference = "Stop"
$루트 = $PSScriptRoot
$파이썬 = Join-Path $루트 "backend\.venv\Scripts\python.exe"
$도구 = "tools\backup.py"

Write-Host ""
Write-Host "세권사주타로 백업" -ForegroundColor Yellow
Write-Host "────────────────────────────────────" -ForegroundColor DarkGray

if (-not (Test-Path $파이썬)) {
    Write-Host "✗ 파이썬 환경이 없습니다. backend 에서 .venv 를 먼저 만드세요." -ForegroundColor Red
    exit 1
}

$인자 = @($도구)
if ($목록)   { $인자 += "--목록" }
if ($검증)   { $인자 += @("--검증", $검증) }
if ($복원)   { $인자 += @("--복원", $복원) }
if ($키제외) { $인자 += "--키제외" }

Push-Location (Join-Path $루트 "backend")
try {
    & $파이썬 @인자
} finally {
    Pop-Location
}
