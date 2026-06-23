@echo off
REM ============================================
REM  SODA Local Agent - Boot Task Installer
REM  Run this as Administrator!
REM ============================================
echo.
echo SODA Local Agent - Boot Service Installer
echo ==========================================
echo.

:: Check admin rights
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Must run as Administrator!
    echo Right-click this file ^> "Run as administrator"
    echo.
    pause
    exit /b 1
)

set "TASK_NAME=SODA Local Agent"
set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%run_agent_boot.bat"

echo Installing scheduled task: %TASK_NAME%
echo Script: %BAT_FILE%
echo.

:: Remove old task if exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Removing existing task...
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

:: Create new task - runs at system startup as SYSTEM, no desktop interaction needed
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "cmd.exe /c \"%BAT_FILE%\"" ^
    /sc onstart ^
    /ru SYSTEM ^
    /rl highest ^
    /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS! Task installed.
    echo The agent will start automatically at every Windows boot.
    echo.
    echo To start NOW (without rebooting):
    echo   schtasks /run /tn "%TASK_NAME%"
    echo.
    echo To check status:
    echo   schtasks /query /tn "%TASK_NAME%" /v ^| findstr Status
    echo   type "%SCRIPT_DIR%agent_boot.log"
    echo.
    echo To remove:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
    echo.
) else (
    echo.
    echo FAILED to create task. Try running as Administrator.
    echo.
)

pause
