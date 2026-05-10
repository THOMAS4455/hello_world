@echo off
setlocal

cd /d "%~dp0"

echo [INFO] Starting project with one click...
echo [INFO] Project root: %cd%

echo [STEP] Launching scripts\start_project.ps1 ...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_project.ps1"
if %errorlevel% neq 0 (
  echo [WARN] PowerShell launcher failed. Fallback to Python launcher...
  start "" /b py -3 ".\scripts\start_bachelor_project.py"
)

echo [STEP] Waiting services to come up...
timeout /t 8 /nobreak >nul

set BACK_OK=0
set FRONT_OK=0

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8000 .*LISTENING"') do set BACK_PID=%%p
if defined BACK_PID set BACK_OK=1

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":3000 .*LISTENING"') do set FRONT_PID=%%p
if defined FRONT_PID set FRONT_OK=1

if "%BACK_OK%"=="1" (
  echo [OK] Backend is listening on 8000 ^(PID: %BACK_PID%^)
) else (
  echo [ERR] Backend is NOT listening on 8000
)

if "%FRONT_OK%"=="1" (
  echo [OK] Frontend is listening on 3000 ^(PID: %FRONT_PID%^)
) else (
  echo [ERR] Frontend is NOT listening on 3000
)

if "%BACK_OK%"=="1" if "%FRONT_OK%"=="1" (
  echo [DONE] Project started successfully.
  start "" http://localhost:3000
) else (
  echo [HINT] Check logs in .\logs\backend and .\logs\frontend
)

echo.
pause

endlocal
