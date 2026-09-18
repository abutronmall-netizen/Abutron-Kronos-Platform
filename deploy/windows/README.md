# Abutron v2.44 Windows production deployment

This runbook deploys the customer/admin control plane on a new Windows host while keeping MetaTrader 5 and the Kronos trading core native on Windows.

## Production layout

- Windows host: MT5 + Kronos core on `127.0.0.1:8765`.
- Docker: PostgreSQL 16, Redis 7, FastAPI API, admin Nginx, outbox worker, notification worker.
- Optional Caddy overlay: public HTTPS on ports 80/443.
- Mobile: React Native / Expo app uses the same HTTPS origin; `/api/*` is reverse-proxied to FastAPI.
- Windows equity agent: reads live USD MT5 equity and updates the platform routing record.

## 1. Prepare Windows

Install current Windows updates, Git for Windows, Docker Desktop (or Docker Engine with Linux containers), and the broker MetaTrader 5 x64 terminal. Install Python 3.11 x64 for the native Kronos core. Reboot if Docker/WSL requests it.

For a public mobile deployment, point a DNS A/AAAA record such as `trade.example.com` to the server and allow inbound TCP 80/443. Do not expose ports 3000, 8080 or 8765 to the public Internet.

## 2. Install and certify the Kronos Windows core

Use the approved v2.40.4 full core bundle and the v2.40.4 certification-persistence hotfix from the Abutron project files. Keep the core bound to loopback.

For a fresh base bundle that contains `INSTALL_WINDOWS.ps1`, run from an elevated PowerShell:

```powershell
cd C:\Abutron\Core
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_WINDOWS.ps1 -TerminalPath "C:\Path\To\MetaTrader 5\terminal64.exe" -Symbol "XAUUSD"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\START_SERVER.ps1
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/engine-status
```

Keep MT5 logged in to the intended live/demo account. Add `http://127.0.0.1:8765` to MT5 WebRequest allow-list where required by the bridge. Keep AutoTrading disabled until the core/bridge certification checks pass.

## 3. Apply the v2.41 bot-tier router foundation

The project router patch defines the exact live-equity bands and safe switching policy. It is fail-closed and does not switch product managers while an Abutron position is open.

- Flipper: USD 20.00 through 3,000.99.
- Scalper: USD 3,001.00 through 5,000.99.
- Master: USD 5,001.00 through 10,000.00.
- Below USD 20 or above USD 10,000: disabled/HOLD.

Important production gate: the supplied v2.41 foundation certifies routing and the existing Scalper strategy identity. Its own README marks Flipper and Master execution engines as foundation-only until dedicated execution-policy tests pass. Do not enable those two products for live orders merely because the router selects their tier.

## 4. Clone the production platform branch

```powershell
New-Item -ItemType Directory -Path C:\Abutron -Force | Out-Null
cd C:\Abutron
git clone https://github.com/abutronmall-netizen/Abutron-Kronos-Platform.git Platform
cd C:\Abutron\Platform
git checkout production/v2.44.0-windows-release
```

## 5. Install the control plane

Local-only install:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\INSTALL_PLATFORM.ps1 -AdminEmail "admin@yourdomain.com"
```

Public HTTPS + Expo push-ready install:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\INSTALL_PLATFORM.ps1 `
  -AdminEmail "admin@yourdomain.com" `
  -PublicHost "trade.yourdomain.com" `
  -EnableExpoPush
```

The installer generates database/JWT/service/engine/billing secrets, runs migrations/catalog bootstrap, creates the administrator, removes bootstrap credentials from future containers, starts health-checked services and stores integration tokens under `C:\ProgramData\Abutron\secrets`.

Do not pass `-EnableKronosPush` until the Windows core actually exposes and authenticates `PUT /platform/v1/account-assignment`. The current native core artifacts do not yet prove that endpoint exists.

## 6. Verify

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\VERIFY_PLATFORM.ps1
docker compose ps
```

Expected local admin URL: `http://127.0.0.1:3000`. With `-PublicHost`, use `https://<your-host>`.

## 7. Configure brokers and customers

Sign into the admin console. In **Operations**, create each broker record, verify broker referrals for eligible 70% discounts, create/adjust billing plans and queue customer notifications.

Customers can register in the mobile app and link an MT5 account by selecting an active broker and entering the MT5 login/server.

## 8. Install the live equity agent for each local MT5 terminal

After the customer account exists in the platform, copy its account UUID from the admin/API and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\INSTALL_EQUITY_AGENT.ps1 `
  -AccountId "PUT-PLATFORM-ACCOUNT-UUID-HERE" `
  -ExpectedLogin 12345678 `
  -TerminalPath "C:\Path\To\MetaTrader 5\terminal64.exe"
```

The agent validates the terminal login and USD account currency before sending live equity. It runs as a highest-privilege logon task. On an MT5 VPS, disconnect the RDP session instead of signing out.

## 9. Build Android and iOS

```powershell
cd C:\Abutron\Platform\mobile
Copy-Item .env.example .env
notepad .env
# Set EXPO_PUBLIC_ABUTRON_API_URL=https://trade.yourdomain.com
powershell.exe -ExecutionPolicy Bypass -File .\SETUP.ps1
npm install -g eas-cli
eas login
eas init
# Put the generated EAS project ID in app.json
eas build -p android --profile preview
eas build -p android --profile production
eas build -p ios --profile production
```

Android push requires FCM v1 credentials in the EAS project. iOS production signing/push requires an Apple Developer account. Never embed service/admin/database secrets in the mobile `.env`; it contains only the public HTTPS API origin.

## 10. Backups

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\BACKUP_PLATFORM.ps1
```

Restore only during a maintenance window:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\windows\RESTORE_PLATFORM.ps1 -BackupDir "C:\AbutronBackups\YYYYMMDD-HHMMSS" -ConfirmRestore
```

The backup includes a PostgreSQL custom-format dump and the production `.env`; the backup directory therefore contains secrets and must be access-controlled and copied to encrypted/off-host storage.

## 11. Go-live gates

The platform/admin/API/mobile source must have green backend/admin/mobile CI. The native core must pass its own test suite and demo certification. Scalper can only go live after core/bridge certification. Flipper and Master remain blocked until their dedicated strategy engines and regression tests are completed and certified.
