<#
.SYNOPSIS
    Install SODA Local Agent as a Windows scheduled task that runs at system boot.
    Must be run as Administrator.

.DESCRIPTION
    This script creates a scheduled task that:
    - Starts automatically at Windows boot (before any user logs in)
    - Runs the SODA Local Agent in the background
    - Restarts automatically if it crashes (up to 3 times)
    - Logs all output to agent_boot.log
    
.EXAMPLE
    Right-click → "Run with PowerShell" (Run as Administrator)
    Or from admin terminal:
    powershell -ExecutionPolicy Bypass -File install_boot_service.ps1
#>

$ErrorActionPreference = "Stop"
$taskName = "SODA Local Agent"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batPath = Join-Path $scriptDir "run_agent_boot.bat"
$logFile = Join-Path $scriptDir "install_boot.log"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SODA Local Agent - Boot Service Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Admin ──
$isAdmin = ([System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click this file → 'Run with PowerShell' (Run as Administrator)" -ForegroundColor Yellow
    Write-Host "Or run from an admin terminal:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Check files exist ──
if (-not (Test-Path $batPath)) {
    Write-Host "ERROR: run_agent_boot.bat not found at: $batPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$agentScript = Join-Path $scriptDir "backend\local_agent.py"
if (-not (Test-Path $agentScript)) {
    Write-Host "ERROR: backend\local_agent.py not found at: $agentScript" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Check Python ──
$pythonOk = $false
$pathsToCheck = @(
    "C:\Users\Abir\AppData\Local\Programs\Python\Python311\pythonw.exe",
    "C:\Program Files\Python311\pythonw.exe",
    "C:\Python311\pythonw.exe"
)
foreach ($p in $pathsToCheck) {
    if (Test-Path $p) {
        $pythonOk = $true
        break
    }
}
if (-not $pythonOk) {
    try {
        $null = Get-Command "pythonw.exe" -ErrorAction Stop
        $pythonOk = $true
    } catch {
        try {
            $null = Get-Command "py" -ErrorAction Stop
            $pythonOk = $true
        } catch {}
    }
}
if (-not $pythonOk) {
    Write-Host "WARNING: Python 3.11 not found at common paths." -ForegroundColor Yellow
    Write-Host "The batch file will search for pythonw.exe at runtime." -ForegroundColor Yellow
    Write-Host "Edit run_agent_boot.bat to set the correct PYTHON path." -ForegroundColor Yellow
}

# ── Remove existing task ──
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task '$taskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# ── Create Task ──
Write-Host "Creating scheduled task..." -ForegroundColor Cyan

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batPath`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -Priority 7

# Run as SYSTEM (highest available, no password needed at boot)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host ""
Write-Host "✓ Task '$taskName' installed successfully!" -ForegroundColor Green
Write-Host "  Trigger: At system startup" -ForegroundColor White
Write-Host "  User:    SYSTEM (runs before login)" -ForegroundColor White
Write-Host "  Restart: 3 retries, 1 min apart" -ForegroundColor White
Write-Host "  Log:     $logFile" -ForegroundColor White
Write-Host ""

# ── Start immediately ──
Write-Host "Starting task now..." -ForegroundColor Cyan
try {
    Start-ScheduledTask -TaskName $taskName
    Write-Host "✓ Task started!" -ForegroundColor Green
} catch {
    Write-Host "Could not start task (may need reboot): $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "To check status later:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName '$taskName' | fl" -ForegroundColor White
Write-Host "  Get-ScheduledTaskInfo -TaskName '$taskName'" -ForegroundColor White
Write-Host "  Get-Content '$scriptDir\agent_boot.log' -Tail 10" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
