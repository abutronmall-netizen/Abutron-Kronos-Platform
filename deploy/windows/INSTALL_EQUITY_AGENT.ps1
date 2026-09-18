param(
  [Parameter(Mandatory=$true)][string]$AccountId,
  [Parameter(Mandatory=$true)][long]$ExpectedLogin,
  [Parameter(Mandatory=$true)][string]$TerminalPath,
  [string]$PythonExe = "python",
  [string]$PlatformOrigin = "http://127.0.0.1:3000",
  [int]$PollSeconds = 15
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
$Agent = Join-Path $Root "agent\windows_mt5_equity_agent.py"
$ServiceToken = Join-Path $env:ProgramData "Abutron\secrets\service-token.txt"
if (-not (Test-Path $TerminalPath)) { throw "MT5 terminal not found: $TerminalPath" }
if (-not (Test-Path $ServiceToken)) { throw "Service token not found. Install the platform first." }

$pythonCommand = Get-Command $PythonExe -ErrorAction Stop
$pythonPath = $pythonCommand.Source
& $pythonPath -m pip install --disable-pip-version-check MetaTrader5
if ($LASTEXITCODE -ne 0) { throw "MetaTrader5 Python package installation failed." }

$AgentDir = Join-Path $env:ProgramData "Abutron\agents"
New-Item -ItemType Directory -Path $AgentDir -Force | Out-Null
$ConfigPath = Join-Path $AgentDir ("equity-" + $AccountId + ".json")
$config = @{
  account_id = $AccountId
  expected_login = $ExpectedLogin
  terminal_path = $TerminalPath
  platform_origin = $PlatformOrigin
  poll_seconds = $PollSeconds
  service_token_file = $ServiceToken
} | ConvertTo-Json
[System.IO.File]::WriteAllText($ConfigPath, $config, (New-Object System.Text.UTF8Encoding($false)))

$TaskName = "Abutron-EquitySync-" + $AccountId.Substring(0, [Math]::Min(8, $AccountId.Length))
$Action = New-ScheduledTaskAction -Execute $pythonPath -Argument ("`"" + $Agent + "`" --config `"" + $ConfigPath + "`"")
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed and started $TaskName" -ForegroundColor Green
Write-Host "Config: $ConfigPath"
Write-Host "Keep the Windows trading session logged in; disconnect RDP instead of signing out."
