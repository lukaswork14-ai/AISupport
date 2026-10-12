# Cài đặt trên Windows. Mở PowerShell trong thư mục này rồi chạy:
#   Set-ExecutionPolicy -Scope Process Bypass; .\install_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Chưa có Python. Cài từ https://www.python.org/downloads/ (tick 'Add python.exe to PATH') rồi chạy lại."
    exit 1
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path .env)) { & .\.venv\Scripts\python.exe setup.py }

if (Test-Path credentials.json) {
    & .\.venv\Scripts\python.exe google_auth.py
} else {
    Write-Host "Chưa có credentials.json nên bỏ qua kết nối Google. Làm theo README rồi chạy: .\.venv\Scripts\python.exe google_auth.py"
}

# Không cho máy ngủ khi cắm điện, để agent chạy 24/7
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

# Tự chạy ngầm mỗi khi đăng nhập Windows
$py = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$main = Join-Path $PSScriptRoot "main.py"
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$main`"" -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "AgentArmy" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "AgentArmy"
Write-Host "Xong. Bot đang chạy ngầm. Hãy nhắn thử cho bot trên Telegram."
