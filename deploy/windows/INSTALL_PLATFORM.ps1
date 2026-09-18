param(
  [string]$AdminEmail = "admin@abutron.local",
  [string]$AdminName = "Abutron Administrator",
  [string]$PublicHost = "",
  [switch]$EnableKronosPush,
  [switch]$EnableExpoPush,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
Set-Location $Root

function New-HexSecret([int]$Bytes = 32) {
  $buffer = New-Object byte[] $Bytes
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
  return -join ($buffer | ForEach-Object { $_.ToString("x2") })
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Invoke-Checked([string]$Label, [scriptblock]$Command) {
  Write-Host "==> $Label" -ForegroundColor Cyan
  & $Command
  if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

Write-Host "Abutron Platform v2.44 - Windows production installer" -ForegroundColor Green
Write-Host "Repository: $Root"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker Desktop / Docker Engine with docker compose is required."
}
Invoke-Checked "Docker version" { docker version }
Invoke-Checked "Docker Compose version" { docker compose version }

$envPath = Join-Path $Root ".env"
if ((Test-Path $envPath) -and -not $Force) {
  throw ".env already exists. Back it up or rerun with -Force."
}

$secureAdmin = Read-Host "Enter the initial Abutron administrator password (12+ characters)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureAdmin)
try { $adminPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if ($adminPassword.Length -lt 12) { throw "Administrator password must be at least 12 characters." }

$dbPassword = New-HexSecret 24
$jwtSecret = New-HexSecret 48
$serviceToken = New-HexSecret 48
$engineToken = New-HexSecret 48
$billingSecret = New-HexSecret 48
$pushEnabled = if ($EnableExpoPush) { "true" } else { "false" }
$kronosEnabled = if ($EnableKronosPush) { "true" } else { "false" }
$origin = if ($PublicHost) { "https://$PublicHost" } else { "http://localhost:3000" }

$lines = @(
  "ABUTRON_ENV=production",
  "ABUTRON_API_HOST=0.0.0.0",
  "ABUTRON_API_PORT=8080",
  "ABUTRON_ADMIN_BIND=127.0.0.1",
  "ABUTRON_ADMIN_PORT=3000",
  "ABUTRON_POSTGRES_DB=abutron",
  "ABUTRON_POSTGRES_USER=abutron",
  "ABUTRON_POSTGRES_PASSWORD=$dbPassword",
  "ABUTRON_DATABASE_URL=postgresql+asyncpg://abutron:$dbPassword@postgres:5432/abutron",
  "ABUTRON_REDIS_URL=redis://redis:6379/0",
  "ABUTRON_JWT_SECRET=$jwtSecret",
  "ABUTRON_JWT_ISSUER=abutron-platform",
  "ABUTRON_ACCESS_TOKEN_MINUTES=30",
  "ABUTRON_SERVICE_TOKEN=$serviceToken",
  "ABUTRON_KRONOS_ENGINE_URL=http://host.docker.internal:8765",
  "ABUTRON_KRONOS_ENGINE_TOKEN=$engineToken",
  "ABUTRON_KRONOS_PUSH_ENABLED=$kronosEnabled",
  "ABUTRON_PUSH_GATEWAY_ENABLED=$pushEnabled",
  "ABUTRON_PUSH_GATEWAY_URL=https://exp.host/--/api/v2/push/send",
  "ABUTRON_PUSH_GATEWAY_TOKEN=",
  "ABUTRON_BILLING_WEBHOOK_SECRET=$billingSecret",
  "ABUTRON_AUTO_CREATE_SCHEMA=false",
  "ABUTRON_CORS_ORIGINS=$origin",
  "ABUTRON_BOOTSTRAP_ADMIN_EMAIL=$AdminEmail",
  "ABUTRON_BOOTSTRAP_ADMIN_PASSWORD=$adminPassword",
  "ABUTRON_BOOTSTRAP_ADMIN_NAME=$AdminName"
)
if ($PublicHost) { $lines += "ABUTRON_PUBLIC_HOST=$PublicHost" }
Write-Utf8NoBom $envPath (($lines -join [Environment]::NewLine) + [Environment]::NewLine)

$secretDir = Join-Path $env:ProgramData "Abutron\secrets"
New-Item -ItemType Directory -Path $secretDir -Force | Out-Null
Write-Utf8NoBom (Join-Path $secretDir "kronos-engine-token.txt") $engineToken
Write-Utf8NoBom (Join-Path $secretDir "service-token.txt") $serviceToken
Write-Utf8NoBom (Join-Path $secretDir "billing-webhook-secret.txt") $billingSecret
try {
  & icacls $secretDir /inheritance:r /grant:r "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null
} catch { Write-Warning "Could not tighten ACLs on $secretDir. Secure this folder manually." }

Invoke-Checked "Validate Compose" { docker compose config -q }
Invoke-Checked "Build and start PostgreSQL, Redis, API, admin and workers" { docker compose up --build -d }

Write-Host "Waiting for API readiness..."
$deadline = (Get-Date).AddMinutes(4)
$ready = $false
while ((Get-Date) -lt $deadline) {
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:3000/health/ready" -TimeoutSec 5
    if ($r.status -eq "ready") { $ready = $true; break }
  } catch { Start-Sleep -Seconds 4 }
}
if (-not $ready) {
  docker compose ps
  docker compose logs --tail 120 api migrate
  throw "Abutron API did not become ready."
}

Invoke-Checked "Bootstrap administrator" { docker compose exec -T api python -m app.bootstrap }

# Remove bootstrap credentials from future container recreations.
$safeLines = Get-Content $envPath | Where-Object { $_ -notmatch "^ABUTRON_BOOTSTRAP_ADMIN_(EMAIL|PASSWORD|NAME)=" }
Write-Utf8NoBom $envPath (($safeLines -join [Environment]::NewLine) + [Environment]::NewLine)
Invoke-Checked "Recreate long-running services without bootstrap credentials" { docker compose up -d --force-recreate api outbox-worker notification-worker }

if ($PublicHost) {
  Invoke-Checked "Start HTTPS gateway" { docker compose -f docker-compose.yml -f deploy/windows/docker-compose.public.yml up -d caddy }
  Write-Host "HTTPS origin: https://$PublicHost" -ForegroundColor Green
} else {
  Write-Warning "No -PublicHost supplied. The platform is local-only at http://127.0.0.1:3000 until an HTTPS hostname is configured."
}

Write-Host ""
Write-Host "INSTALL COMPLETE" -ForegroundColor Green
Write-Host "Admin URL: $origin"
Write-Host "API health: $origin/health/ready"
Write-Host "Kronos engine URL expected by platform: http://host.docker.internal:8765"
Write-Host "Kronos engine token file: $secretDir\kronos-engine-token.txt"
Write-Host "Service token file: $secretDir\service-token.txt"
Write-Host "Kronos push enabled: $kronosEnabled"
Write-Host ""
docker compose ps
