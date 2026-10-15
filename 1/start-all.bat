@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ============================================================================
rem  ZhiTong LingSheng - Dev Env Start   (rewritten 2026-10-06 by DSH)
rem ----------------------------------------------------------------------------
rem  Why rewritten - three real problems found by actually testing:
rem
rem  1) Double-start hit the port. The old script started the backend blindly;
rem     if 8001 was already listening, uvicorn threw
rem     [Errno 10048] address already in use and the window vanished -
rem     it looked like "the script is broken". Now we PROBE the port first:
rem     if something is already listening we skip it and say so, so an
rem     already-running backend is never disturbed.
rem
rem  2) --reload fought the model loading. The old backend ran with --reload,
rem     so every backend edit restarted the whole process, and
rem     realtime_detector / ultralytics / torch module-level loading is heavy -
rem     demos suffered long stalls and zombie processes. Default is now
rem     NO --reload, matching the instance that was already running:
rem       python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
rem     Need auto-reload while editing:  start-all.bat --reload
rem
rem  3) node was not on PATH. This machine has node at E:\node.exe
rem     (non-standard). We now probe E:\node.exe -> where node.
rem
rem  NOTE: this file must stay ASCII-only. cmd.exe parses the whole script
rem  BEFORE chcp takes effect, so UTF-8/GBK Chinese comments break the parser
rem  (verified the hard way: "not recognized as an internal command").
rem  Chinese docs live in _STARTUP_GUIDE.md instead.
rem ============================================================================

echo =========================================
echo   ZhiTong LingSheng - Dev Env Start
echo   Project Dir: %~dp0
echo =========================================
echo.

set "WITH_RELOAD=0"
if /i "%~1"=="--reload" set "WITH_RELOAD=1"

rem ============================================================================
rem  Backend tuning - set HERE so start-all.bat and restart-backend.bat agree.
rem ----------------------------------------------------------------------------
rem  Why these values (measured 2026-10-06, not guesses - see _PERF_FPS_verdict.md):
rem
rem   Problem: "detection boxes cannot keep up with the cars".
rem   Finding: end-to-end throughput was only ~1.8 fps (one frame = 480-560 ms),
rem            while model inference itself needs just 139 ms. Between two
rem            detections the video advances 0.30 s (6 frames at 20 fps), so the
rem            boxes only moved twice a second.
rem
rem   YOLO_IMGSZ=960       1280 -> 960 cuts preprocess cost; small targets
rem                        (traffic light, plate) still detected.
rem   FRAME_RATE=6         raise the detection budget from 3 to 6 fps.
rem   YOLO_MODEL_SEQUENCE  DROP license_plate: its .pt file does NOT exist, so it
rem                        silently fell back to the COCO yolov8s model and
rem                        returned 12 garbage boxes per frame (fire hydrant,
rem                        potted plant, sports ball) while costing ~30 ms.
rem                        helmet + lane are KEPT on purpose (features must not
rem                        be traded away for speed).
rem   BOX_PREDICTION=1     between detections, extrapolate each box using the
rem                        vehicle's recent displacement so the boxes slide with
rem                        the cars instead of jumping. Display-only: it never
rem                        writes back to the tracker, so violation decisions and
rem                        speed measurement are unaffected. Set to 0 to disable.
rem
rem  To go back to the old behaviour: comment out these four lines.
rem ============================================================================
set "TUNE_IMGSZ=960"
set "TUNE_FRAME_RATE=6"
set "TUNE_MODEL_SEQUENCE=vehicle,traffic_light,helmet,lane"
set "TUNE_BOX_PREDICTION=1"

rem ---- Python interpreter (deps live in conda env zhitong-gpu) ----
set "PYEXE="
if exist "C:\miniconda\envs\zhitong-gpu\python.exe" set "PYEXE=C:\miniconda\envs\zhitong-gpu\python.exe"
if not defined PYEXE for /f "delims=" %%i in ('where python 2^>nul') do if not defined PYEXE set "PYEXE=%%i"
if not defined PYEXE set "PYEXE=py -3"

rem ---- Node (this machine: E:\node.exe) ----
set "NODEEXE="
if exist "E:\node.exe" set "NODEEXE=E:\node.exe"
if not defined NODEEXE for /f "delims=" %%i in ('where node 2^>nul') do if not defined NODEEXE set "NODEEXE=%%i"

echo   Python : %PYEXE%
if defined NODEEXE (echo   Node   : %NODEEXE%) else (echo   Node   : NOT FOUND - frontend cannot start)
if "%WITH_RELOAD%"=="1" (echo   Reload : ON) else (echo   Reload : OFF  [use restart-backend.bat after backend edits])
echo   Tuning : imgsz=%TUNE_IMGSZ%  frame_rate=%TUNE_FRAME_RATE%  box_prediction=%TUNE_BOX_PREDICTION%
echo            models=%TUNE_MODEL_SEQUENCE%
echo.

echo [1/3] Backend API (port 8001)
netstat -ano | findstr /r /c:"TCP.*:8001 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo   [SKIP] port 8001 already listening - reusing the running backend.
  echo          To restart after code edits: restart-backend.bat
) else (
  if "%WITH_RELOAD%"=="1" (
    start "ZhiTong Backend API" cmd /k cd /d %~dp0 ^&^& set "PYTHONPATH=%~dp0api;%~dp0" ^&^& set "YOLO_IMGSZ=%TUNE_IMGSZ%" ^&^& set "FRAME_RATE=%TUNE_FRAME_RATE%" ^&^& set "YOLO_MODEL_SEQUENCE=%TUNE_MODEL_SEQUENCE%" ^&^& set "BOX_PREDICTION=%TUNE_BOX_PREDICTION%" ^&^& "%PYEXE%" -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
  ) else (
    start "ZhiTong Backend API" cmd /k cd /d %~dp0 ^&^& set "PYTHONPATH=%~dp0api;%~dp0" ^&^& set "YOLO_IMGSZ=%TUNE_IMGSZ%" ^&^& set "FRAME_RATE=%TUNE_FRAME_RATE%" ^&^& set "YOLO_MODEL_SEQUENCE=%TUNE_MODEL_SEQUENCE%" ^&^& set "BOX_PREDICTION=%TUNE_BOX_PREDICTION%" ^&^& "%PYEXE%" -m uvicorn app:app --host 127.0.0.1 --port 8001
  )
  echo   started, waiting 5s ...
  timeout /t 5 /nobreak >nul
)
echo.

echo [2/3] Web Admin (port 5173)
netstat -ano | findstr /r /c:"TCP.*:5173 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo   [SKIP] port 5173 already listening - frontend is already running.
) else (
  if not defined NODEEXE (
    echo   [FAIL] node not found. Install Node.js or put node.exe in E:\
  ) else (
    start "ZhiTong Web Admin" cmd /k cd /d %~dp0web-admin ^&^& set "PATH=E:\;%%PATH%%" ^&^& npm run dev
    echo   started, waiting 6s ...
    timeout /t 6 /nobreak >nul
  )
)
echo.

echo [3/3] Opening browser...
echo =========================================
echo   Startup Complete
echo   - Web Admin : http://localhost:5173
echo   - API Docs  : http://127.0.0.1:8001/docs
echo   - Health    : http://127.0.0.1:8001/health
echo =========================================
echo.
echo Tips:
echo   - backend code changed  -^> run restart-backend.bat
echo   - frontend only         -^> nothing to do, vite hot-reloads
echo   - stop services         -^> close the black windows
echo.
start http://localhost:5173
pause
