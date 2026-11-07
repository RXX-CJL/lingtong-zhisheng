@echo off
REM Pure ASCII only. cmd reads .bat as GBK; UTF-8 Chinese breaks parsing.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0src"

REM Use the absolute python path so double-click always works,
REM even if PATH is different from this shell.
set PY=C:\Users\ROG\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python

echo ============================================================
echo   PoXiao ChaoXi - Music Responsive Fountain
echo ============================================================
echo.
echo   Playing any sound on this PC will drive the 11 nozzles.
echo   Use headphones/speaker output - NOT the microphone.
echo.
echo   Press Ctrl+C to quit.
echo ============================================================
echo.

"%PY%" fountain.py %*
echo.
echo [exited]
pause
