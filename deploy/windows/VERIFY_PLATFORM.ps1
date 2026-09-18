$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
Set-Location $Root
Write-Host "=== Abutron Platform Verification ===" -ForegroundColor Cyan
docker compose ps
if ($LASTEXITCODE -ne 0) { throw "docker compose ps failed" }
$ready = Invoke-RestMethod -Uri "http://127.0.0.1:3000/health/ready" -TimeoutSec 10
if ($ready.status -ne "ready") { throw "Platform health check failed" }
Write-Host "Platform API: READY" -ForegroundColor Green
try {
  $core = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 10
  Write-Host "Kronos core: reachable on 127.0.0.1:8765" -ForegroundColor Green
} catch {
  Write-Warning "Kronos core is not reachable on 127.0.0.1:8765. Start the Windows core before live trading."
}
try {
  Invoke-WebRequest -UseBasicParsing -Uri "https://exp.host/" -Method Head -TimeoutSec 10 | Out-Null
  Write-Host "Expo push network path: reachable" -ForegroundColor Green
} catch {
  Write-Warning "Expo push endpoint not reachable from this server."
}
Write-Host "Verification complete." -ForegroundColor Green
