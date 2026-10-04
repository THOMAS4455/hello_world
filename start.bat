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
echo [INFO] Backend usually ready in ~10s; frontend (React) may take 30-90s on first compile...

set BACK_OK=0
set FRONT_OK=0
set BACK_PID=
set FRONT_PID=
set /a WAIT_ROUND=0

:wait_loop
set /a WAIT_ROUND+=1
set BACK_PID=
set FRONT_PID=
set BACK_OK=0
set FRONT_OK=0

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8000 .*LISTENING"') do set BACK_PID=%%p
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":3000 .*LISTENING"') do set FRONT_PID=%%p

rem Readiness means "answers HTTP 200", not just "the port is bound". The React dev
rem server binds port 3000 while it is still compiling, so a port-only check would
rem open the browser on a page that has nothing to serve yet.
for /f %%s in ('powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri http://127.0.0.1:8000/health -TimeoutSec 3 -UseBasicParsing).StatusCode}catch{0}"') do set BACK_CODE=%%s
if "%BACK_CODE%"=="200" set BACK_OK=1

for /f %%s in ('powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri http://127.0.0.1:3000 -TimeoutSec 3 -UseBasicParsing).StatusCode}catch{0}"') do set FRONT_CODE=%%s
if "%FRONT_CODE%"=="200" set FRONT_OK=1

if "%BACK_OK%"=="1" if "%FRONT_OK%"=="1" goto check_done

if %WAIT_ROUND% GEQ 36 (
  echo [WARN] Timed out after ~180s waiting for both services to answer HTTP. First
  echo        frontend start compiles the bundle and can exceed two minutes.
  goto check_done
)

echo [WAIT] Round %WAIT_ROUND%: backend=%BACK_OK% frontend=%FRONT_OK% ...
timeout /t 5 /nobreak >nul
goto wait_loop

:check_done

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
  if "%BACK_OK%"=="1" (
    echo [PARTIAL] Backend is up. Frontend still compiling - wait 1-2 min then open:
    echo          http://localhost:3000
    start "" http://localhost:3000
  )
  echo [HINT] Check logs in .\logs\backend and .\logs\frontend
)

echo.
pause

endlocal
