@echo off
REM ============================================================
REM  CodeBuddy CLI 启动器（WorkBuddy 内置的腾讯 agent CLI）
REM  路径来源：F:\AI\WorkBuddy\resources\app.asar.unpacked\cli
REM  ★ 必须设 CODEBUDDY_FORCE_LITE_WB_BUNDLE=1 —— 本机只装了
REM    lite-wb 变体（dist\codebuddy-lite-wb.mjs），不设这个变量
REM    会去 require('../dist/codebuddy') 而报 MODULE_NOT_FOUND
REM ============================================================
REM  用法：
REM    codebuddy.cmd                        进入交互模式（首次输入 /login 登录）
REM    codebuddy.cmd -p "任务"               非交互派活（等价 codex exec）
REM    codebuddy.cmd -p "任务" --output-format json
REM    codebuddy.cmd --model kimi-k2.5 -p "任务"
REM    codebuddy.cmd --serve --port 56516    起 REST API / Web UI
REM ============================================================
setlocal
set "CODEBUDDY_FORCE_LITE_WB_BUNDLE=1"
set "CBC=F:\AI\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy"
if not exist "%CBC%" (
  echo [错误] 找不到 CodeBuddy CLI: %CBC%
  echo        请确认 WorkBuddy 是否仍安装在 F:\AI\WorkBuddy
  exit /b 1
)
node "%CBC%" %*
exit /b %ERRORLEVEL%
