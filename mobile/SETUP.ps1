$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 22.13+ is required." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created mobile .env - set EXPO_PUBLIC_ABUTRON_API_URL before building." }
npm install --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
npm run setup
if ($LASTEXITCODE -ne 0) { throw "Expo dependency setup failed" }
npm run typecheck
if ($LASTEXITCODE -ne 0) { throw "TypeScript validation failed" }
npx expo-doctor
if ($LASTEXITCODE -ne 0) { throw "Expo Doctor reported a blocking issue" }
Write-Host "Mobile source is ready."
Write-Host "Android preview: npx eas build -p android --profile preview"
Write-Host "Production: npx eas build -p android --profile production / npx eas build -p ios --profile production"
