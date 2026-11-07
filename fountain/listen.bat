@echo off
REM Pure ASCII only. cmd reads .bat as GBK; UTF-8 Chinese would break parsing.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0src"
echo.
echo ================================================================
echo  PoXiao ChaoXi  -  System Audio Listener  (WASAPI Loopback)
echo ================================================================
echo  Close this window or press Ctrl+C to stop.
echo.
python listen.py %*
echo.
pause
