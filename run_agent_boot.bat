@echo off
REM SODA Local Agent - Boot-time launcher for Task Scheduler
REM Uses pythonw.exe (no console window) and logs all output.

set "AGENT_DIR=%~dp0backend"
set "LOG_FILE=%~dp0agent_boot.log"

echo [%date% %time%] Starting SODA Agent... >> "%LOG_FILE%"

set "PYTHON="
if exist "C:\Users\Abir\AppData\Local\Programs\Python\Python311\pythonw.exe" set "PYTHON=C:\Users\Abir\AppData\Local\Programs\Python\Python311\pythonw.exe"
if not defined PYTHON if exist "C:\Program Files\Python311\pythonw.exe" set "PYTHON=C:\Program Files\Python311\pythonw.exe"
if not defined PYTHON for /f "tokens=*" %%a in ('where pythonw 2^>nul') do set "PYTHON=%%a" & goto :found
:found

if not defined PYTHON (
    echo [%date% %time%] ERROR: pythonw.exe not found! >> "%LOG_FILE%"
    exit /b 1
)

echo [%date% %time%] Using: %PYTHON% >> "%LOG_FILE%"
echo [%date% %time%] Script: %AGENT_DIR%\local_agent.py >> "%LOG_FILE%"

start "" "%PYTHON%" -u "%AGENT_DIR%\local_agent.py"

echo [%date% %time%] Agent launched. PID: %ERRORLEVEL% >> "%LOG_FILE%"
