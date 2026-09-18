param(
  [Parameter(Mandatory=$true)][string]$BackupDir,
  [switch]$ConfirmRestore
)
$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Restore is destructive. Rerun with -ConfirmRestore." }
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
Set-Location $Root
$dump = Join-Path $BackupDir "abutron-platform.dump"
$savedEnv = Join-Path $BackupDir "platform.env"
if (-not (Test-Path $dump)) { throw "Backup dump not found: $dump" }
if (Test-Path $savedEnv) { Copy-Item $savedEnv ".env" -Force }
function EnvValue([string]$Name,[string]$Default){
  $line = Get-Content ".env" | Where-Object { $_ -match ("^" + [regex]::Escape($Name) + "=") } | Select-Object -First 1
  if (-not $line) { return $Default }
  return ($line -split "=",2)[1]
}
$db = EnvValue "ABUTRON_POSTGRES_DB" "abutron"
$user = EnvValue "ABUTRON_POSTGRES_USER" "abutron"
docker compose up -d postgres
$cid = (docker compose ps -q postgres).Trim()
if (-not $cid) { throw "PostgreSQL container is not running" }
docker cp $dump ($cid + ":/tmp/abutron-platform.dump")
docker compose stop api admin outbox-worker notification-worker | Out-Null
docker exec $cid pg_restore -U $user -d $db --clean --if-exists --no-owner /tmp/abutron-platform.dump
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }
docker exec $cid rm -f /tmp/abutron-platform.dump | Out-Null
docker compose run --rm migrate
if ($LASTEXITCODE -ne 0) { throw "Migration after restore failed" }
docker compose up -d
Write-Host "Restore complete. Run VERIFY_PLATFORM.ps1 now." -ForegroundColor Green
