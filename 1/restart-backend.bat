@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ============================================================================
rem  ZhiTong LingSheng - Restart Backend (port 8001)   (2026-10-06 by DSH)
rem ----------------------------------------------------------------------------
rem  Why this exists: the backend does NOT hot-reload your edits
rem  (start-all.bat runs without --reload on purpose). Before this script the
rem  only way was to hunt python.exe in Task Manager and risk killing the
rem  wrong process.
rem
rem  What it does:
rem    1) find the PID listening on 8001 (by PORT, never by process name)
rem    2) verify that PID really is python.exe - ABORT if not (no accidental kills)
rem    3) stop it and wait until the port is actually released
rem    4) relaunch with the exact same command, in a visible new window
rem
rem  NOTE: keep this file ASCII-only. cmd.exe parses the script before chcp
rem  takes effect, so non-ASCII comments break the parser (verified).
rem  Chinese docs: _STARTUP_GUIDE.md
rem ============================================================================

echo =========================================
echo   Restart Backend (port 8001)
echo =========================================
echo.

set "PYEXE="
if exist "C:\miniconda\envs\zhitong-gpu\python.exe" set "PYEXE=C:\miniconda\envs\zhitong-gpu\python.exe"
if not defined PYEXE for /f "delims=" %%i in ('where python 2^>nul') do if not defined PYEXE set "PYEXE=%%i"
if not defined PYEXE set "PYEXE=py -3"
echo   Python: %PYEXE%
echo.

set "PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"TCP.*:8001 .*LISTENING"') do set "PID=%%p"

if not defined PID (
  echo   [INFO] nothing is listening on 8001 - starting fresh.
  goto :startit
)

echo   found listener PID=%PID%

set "PNAME="
for /f "delims=" %%n in ('tasklist /fi "PID eq %PID%" /nh /fo csv 2^>nul') do set "PNAME=%%~n"
echo   process name: %PNAME%
echo %PNAME% | findstr /i "python" >nul
if errorlevel 1 (
  echo.
  echo   [ABORT] that PID is not python.exe - refusing to kill it.
  echo           check manually:  tasklist /fi "PID eq %PID%"
  echo.
  pause
  exit /b 1
)

echo   stopping PID=%PID% ...
taskkill /PID %PID% /F >nul 2>&1
set /a _n=0
:waitloop
set /a _n+=1
netstat -ano | findstr /r /c:"TCP.*:8001 .*LISTENING" >nul 2>&1
if errorlevel 1 goto :released
if !_n! geq 20 (
  echo   [WARN] port still busy after 10s - please check manually.
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto :waitloop
:released
echo   port 8001 released.
echo.

:startit
rem ---- Backend tuning: MUST stay identical to start-all.bat ------------------
rem  Otherwise "restart" would silently revert the settings that start-all set,
rem  and the two launchers would produce different behaviour (very confusing).
rem  See start-all.bat for the full rationale and the measurements behind it.
set "TUNE_IMGSZ=960"
set "TUNE_FRAME_RATE=6"
set "TUNE_MODEL_SEQUENCE=vehicle,traffic_light,helmet,lane"
set "TUNE_BOX_PREDICTION=1"

echo   launching backend (cwd = project root, PYTHONPATH includes api and root) ...
echo   tuning: imgsz=%TUNE_IMGSZ% frame_rate=%TUNE_FRAME_RATE% prediction=%TUNE_BOX_PREDICTION%
start "ZhiTong Backend API" cmd /k cd /d %~dp0 ^&^& set "PYTHONPATH=%~dp0api;%~dp0" ^&^& set "YOLO_IMGSZ=%TUNE_IMGSZ%" ^&^& set "FRAME_RATE=%TUNE_FRAME_RATE%" ^&^& set "YOLO_MODEL_SEQUENCE=%TUNE_MODEL_SEQUENCE%" ^&^& set "BOX_PREDICTION=%TUNE_BOX_PREDICTION%" ^&^& "%PYEXE%" -m uvicorn app:app --host 127.0.0.1 --port 8001
echo   waiting 10s, then self-check ...
timeout /t 10 /nobreak >nul

echo.
echo   ---- self check ----
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 10; Write-Host ('  /health       : OK   db=' + $r.db_exists + ' size=' + $r.db_size_bytes + ' yolo=' + $r.yolo_available) } catch { Write-Host '  /health       : not ready yet (backend may still be loading)' }"
powershell -NoProfile -Command "try { $o = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/openapi.json' -TimeoutSec 10; $n = 0; foreach ($p in $o.paths.PSObject.Properties) { foreach ($m in $p.Value.PSObject.Properties) { $n++ } }; Write-Host ('  openapi       : ' + $n + ' operations (expect 132)') } catch { Write-Host '  openapi       : not ready yet' }"
powershell -NoProfile -Command "try { $s = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/realtime/settings' -TimeoutSec 10; Write-Host ('  cloud_review  : ' + $s.data.cloud_review) } catch { Write-Host '  settings      : not ready yet' }"
echo.
echo   Done. Refresh http://localhost:5173
echo.
pause
