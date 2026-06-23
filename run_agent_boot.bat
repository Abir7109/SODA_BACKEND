@echo off
REM SODA Local Agent - Boot launcher for Task Scheduler
REM Uses launch_agent.py to capture all output to agent_launcher.log

set "SCRIPT_DIR=%~dp0"
set "LOG_FILE=%SCRIPT_DIR%agent_boot.log"

echo [%date% %time%] Starting SODA Agent Launcher... >> "%LOG_FILE%"

:: Find Python
set "PYTHON="
if exist "C:\Users\Abir\AppData\Local\Programs\Python\Python311\python.exe" set "PYTHON=C:\Users\Abir\AppData\Local\Programs\Python\Python311\python.exe"
if not defined PYTHON if exist "C:\Program Files\Python311\python.exe" set "PYTHON=C:\Program Files\Python311\python.exe"
if not defined PYTHON set "PYTHON=python"

echo [%date% %time%] Python: %PYTHON% >> "%LOG_FILE%"

:: Launch agent via launcher script (captures stdout/stderr to agent_launcher.log)
start "" "%PYTHON%" -u "%SCRIPT_DIR%launch_agent.py"

echo [%date% %time%] Launcher started >> "%LOG_FILE%"
