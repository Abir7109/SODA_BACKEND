# Hermes Agent Auto-Start Installer for SODA
# Run as Administrator:  powershell -ExecutionPolicy Bypass -File install_hermes_service.ps1
#
# Options:
#   .\install_hermes_service.ps1            - Install as Scheduled Task (auto-start at logon)
#   .\install_hermes_service.ps1 -Action remove  - Remove the Scheduled Task
#   .\install_hermes_service.ps1 -Action start   - Start Hermes gateway now (no admin needed)
#   .\install_hermes_service.ps1 -Action status  - Check if installed and running
#   .\install_hermes_service.ps1 -Action setup   - Full setup: install Hermes + configure + install service

param($Action = "install")

$taskName = "SODA Hermes Agent"
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step($m) { Write-Host "  $m" -ForegroundColor Cyan }
function Write-Ok($m) { Write-Host "  v $m" -ForegroundColor Green }
function Write-Err($m) { Write-Host "  x $m" -ForegroundColor Red }
function Write-Warn($m) { Write-Host "  ! $m" -ForegroundColor Yellow }

$action = $Action.ToLower()

if ($action -eq "setup") {
    Write-Host "`n=== Hermes Agent Full Setup for SODA ===" -ForegroundColor Cyan
    Write-Host ""

    # Step 1: Check if hermes is installed
    Write-Step "Checking if Hermes Agent is installed..."
    $hermesCmd = Get-Command hermes -ErrorAction SilentlyContinue
    if ($hermesCmd) {
        Write-Ok "Hermes Agent found: $($hermesCmd.Source)"
    } else {
        Write-Warn "Hermes Agent not found. Installing..."
        Write-Host "  Running official installer..." -ForegroundColor Gray
        try {
            iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
            Write-Ok "Hermes Agent installed"
            Write-Warn "Open a NEW PowerShell window and re-run this script to continue setup"
            exit 0
        } catch {
            Write-Err "Hermes installation failed: $_"
            Write-Host "  Install manually: https://github.com/NousResearch/hermes-agent" -ForegroundColor Yellow
            exit 1
        }
    }

    # Step 2: Configure API keys
    Write-Host ""
    Write-Step "Configuring Hermes Agent..."

    # Check for existing API keys
    $envFile = "$env:LOCALAPPDATA\hermes\.env"
    $configFile = "$env:LOCALAPPDATA\hermes\config.yaml"

    $hasKey = $false
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        if ($envContent -match "GEMINI_API_KEY|OPENROUTER_API_KEY|GOOGLE_API_KEY") {
            Write-Ok "API key already configured"
            $hasKey = $true
        }
    }

    if (-not $hasKey) {
        Write-Host ""
        Write-Host "  Hermes needs a free LLM API key for computer_use tasks." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  FREE options (no credit card):" -ForegroundColor White
        Write-Host "    1. Google AI Studio (recommended) - https://aistudio.google.com/apikey" -ForegroundColor White
        Write-Host "    2. OpenRouter (auto-picks best free model) - https://openrouter.ai/keys" -ForegroundColor White
        Write-Host ""

        $choice = Read-Host "  Which provider? (1 = Google AI Studio, 2 = OpenRouter) [1]"
        if (-not $choice) { $choice = "1" }

        if ($choice -eq "1") {
            $key = Read-Host "  Paste your Google AI Studio API key (starts with AIza)"
            if ($key) {
                hermes config set GEMINI_API_KEY $key
                hermes config set model.default gemini-2.5-flash
                Write-Ok "Configured Google AI Studio (gemini-2.5-flash)"
            }
        } else {
            $key = Read-Host "  Paste your OpenRouter API key (starts with sk-or-)"
            if ($key) {
                hermes config set OPENROUTER_API_KEY $key
                hermes config set model.default nvidia/nemotron-3-ultra-550b-a55b:free
                Write-Ok "Configured OpenRouter (nvidia/nemotron-3-ultra-550b-a55b:free)"
            }
        }
    }

    # Step 3: Enable API server
    Write-Step "Enabling Hermes API server..."
    hermes config set API_SERVER_ENABLED true
    hermes config set API_SERVER_KEY soda-hermes-local
    Write-Ok "API server enabled on localhost:8642"

    # Step 4: Install computer_use
    Write-Step "Installing computer_use driver..."
    try {
        hermes computer-use install 2>$null
        Write-Ok "computer_use driver installed"
    } catch {
        Write-Warn "computer_use driver install skipped (will try on first use)"
    }

    # Step 5: Install auto-start service
    Write-Host ""
    Write-Step "Installing auto-start service..."
    & $MyInvocation.MyCommand.Path -Action install

    Write-Host ""
    Write-Host "=== SETUP COMPLETE ===" -ForegroundColor Green
    Write-Host "  Hermes Agent will start automatically at logon." -ForegroundColor Green
    Write-Host "  API: http://localhost:8642" -ForegroundColor Gray
    Write-Host "  Key: soda-hermes-local" -ForegroundColor Gray
    Write-Host ""

} elseif ($action -eq "install") {
    Write-Host "`n=== SODA Hermes Agent Auto-Start Installer ===" -ForegroundColor Cyan
    Write-Host ""

    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Primary.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Err "Administrator privileges required."
        Write-Host "  Right-click PowerShell and select 'Run as Administrator', then re-run:" -ForegroundColor Yellow
        Write-Host "    .\install_hermes_service.ps1`n"
        exit 1
    }

    Write-Step "Checking Hermes Agent..."
    $hermesCmd = Get-Command hermes -ErrorAction SilentlyContinue
    if (-not $hermesCmd) {
        Write-Err "Hermes Agent not found on PATH."
        Write-Host "  Run: .\install_hermes_service.ps1 -Action setup" -ForegroundColor Yellow
        exit 1
    }
    Write-Ok "Hermes found: $($hermesCmd.Source)"

    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Step "Removing existing task..."
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Ok "Old task removed"
    }

    Write-Step "Creating Scheduled Task..."
    $schedAction = New-ScheduledTaskAction -Execute "hermes" -Argument "gateway"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask -TaskName $taskName -Action $schedAction -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null
    Write-Ok "Scheduled Task '$taskName' created"

    Write-Host ""
    Write-Host "=== INSTALLATION COMPLETE ===" -ForegroundColor Green
    Write-Host "  Hermes Agent will start automatically at your next logon." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Start Hermes NOW without logging out:" -ForegroundColor Yellow
    Write-Host "    .\install_hermes_service.ps1 -Action start" -ForegroundColor White
    Write-Host ""

} elseif ($action -eq "start") {
    Write-Step "Starting Hermes Agent gateway..."

    # Check if already running
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8642/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Ok "Hermes is already running (HTTP $($resp.StatusCode))"
        exit 0
    } catch {
        # Not running, start it
    }

    try {
        $p = Start-Process -FilePath "hermes" -ArgumentList "gateway" -WindowStyle Hidden -PassThru
        Write-Ok "Hermes gateway started (PID: $($p.Id))"
        Write-Host "  Waiting for API server..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8642/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Ok "API server is live on http://127.0.0.1:8642"
        } catch {
            Write-Warn "API server may still be starting up..."
        }
    } catch {
        Write-Err "Failed to start: $_"
        exit 1
    }

} elseif ($action -eq "remove") {
    Write-Host "`nRemoving SODA Hermes Agent auto-start..." -ForegroundColor Cyan
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Ok "Task '$taskName' removed"
    } else {
        Write-Warn "No task found to remove"
    }
    Write-Host ""

} elseif ($action -eq "status") {
    Write-Host "`n=== SODA Hermes Agent Status ===" -ForegroundColor Cyan
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Ok "Scheduled Task: INSTALLED"
        Write-Host "    State:    $($task.State)" -ForegroundColor Gray
        Write-Host "    Next Run: $($task.NextRunTime)" -ForegroundColor Gray
    } else {
        Write-Warn "Scheduled Task: NOT INSTALLED"
        Write-Host "    Run as Admin: .\install_hermes_service.ps1" -ForegroundColor Yellow
    }

    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8642/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Ok "Hermes Gateway: RUNNING (HTTP $($resp.StatusCode))"
        Write-Host "    URL:  http://127.0.0.1:8642" -ForegroundColor Gray
        Write-Host "    Key:  soda-hermes-local" -ForegroundColor Gray
    } catch {
        Write-Warn "Hermes Gateway: NOT RUNNING"
        Write-Host "    Start it: .\install_hermes_service.ps1 -Action start" -ForegroundColor Yellow
    }

    $hermesProcesses = Get-Process -Name "hermes*" -ErrorAction SilentlyContinue
    if ($hermesProcesses) {
        Write-Ok "Hermes processes: $($hermesProcesses.Count) running"
    } else {
        Write-Warn "No Hermes processes found"
    }
    Write-Host ""

} else {
    Write-Host "`nUsage:" -ForegroundColor Cyan
    Write-Host "  setup     - Full setup: install + configure + install service (recommended first run)" -ForegroundColor White
    Write-Host "  install   - Register Hermes to auto-start on Windows logon (requires admin)" -ForegroundColor White
    Write-Host "  start     - Start Hermes gateway right now (no admin needed)" -ForegroundColor White
    Write-Host "  remove    - Unregister the auto-start task" -ForegroundColor White
    Write-Host "  status    - Check if auto-start is installed and gateway is running" -ForegroundColor White
    Write-Host ""
}
