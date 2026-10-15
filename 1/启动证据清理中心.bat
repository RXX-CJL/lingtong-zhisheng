@echo off
chcp 65001 >nul
set "TOOL=%~dp0tools\evidence_cleanup_center.py"
if not exist "%TOOL%" (
  echo 找不到证据清理中心脚本：%TOOL%
  pause
  exit /b 1
)
py -3.12 "%TOOL%"
if errorlevel 1 (
  echo.
  echo 工具已退出或启动失败。请确认 Python 3.12 可用。
  pause
)
