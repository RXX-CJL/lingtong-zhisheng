@echo off
chcp 65001 >nul
setlocal
set "PS1=%~dp0lib\minimal.ps1"
where pwsh >nul 2>nul
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
) else (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
)
echo.
pause
