param([string]$Destination = "C:\AbutronBackups")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
Set-Location $Root
if (-not (Test-Path ".env")) { throw ".env not found" }
function EnvValue([string]$Name,[string]$Default){
  $line = Get-Content ".env" | Where-Object { $_ -match ("^" + [regex]::Escape($Name) + "=") } | Select-Object -First 1
  if (-not $line) { return $Default }
  return ($line -split "=",2)[1]
}
$db = EnvValue "ABUTRON_POSTGRES_DB" "abutron"
$user = EnvValue "ABUTRON_POSTGRES_USER" "abutron"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dir = Join-Path $Destination $stamp
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$cid = (docker compose ps -q postgres).Trim()
if (-not $cid) { throw "PostgreSQL container is not running" }
docker exec $cid pg_dump -U $user -d $db -Fc -f /tmp/abutron-platform.dump
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
docker cp ($cid + ":/tmp/abutron-platform.dump") (Join-Path $dir "abutron-platform.dump")
docker exec $cid rm -f /tmp/abutron-platform.dump | Out-Null
Copy-Item ".env" (Join-Path $dir "platform.env")
git rev-parse HEAD 2>$null | Set-Content (Join-Path $dir "git-commit.txt")
try { & icacls $dir /inheritance:r /grant:r "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null } catch {}
Write-Host "Backup created: $dir" -ForegroundColor Green
Write-Warning "platform.env contains production secrets. Store this backup securely."
