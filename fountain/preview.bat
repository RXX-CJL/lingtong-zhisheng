@echo off
REM Pure ASCII only. cmd reads .bat as GBK; UTF-8 Chinese breaks parsing.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0src"

set PY=C:\Users\ROG\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python

echo ============================================================
echo   PREVIEW MODE - does NOT write to MCGS
echo ============================================================
echo.
echo   Shows the 11 nozzle heights on screen so you can check
echo   the analysis without touching the fountain.
echo.
echo   Press Ctrl+C to quit.
echo ============================================================
echo.

"%PY%" fountain.py --dry %*
echo.
echo [exited]
pause
