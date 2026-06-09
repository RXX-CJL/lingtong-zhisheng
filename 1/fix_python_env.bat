@echo off
echo ==============================================
echo      Python环境变量修复脚本
echo ==============================================
echo.

set "PYTHON_PATH=C:\Users\ROG\AppData\Local\Programs\Python\Python312"
set "SCRIPTS_PATH=C:\Users\ROG\AppData\Local\Programs\Python\Python312\Scripts"

echo Python路径: %PYTHON_PATH%
echo Scripts路径: %SCRIPTS_PATH%
echo.

echo 正在检查路径是否存在...
if not exist "%PYTHON_PATH%\python.exe" (
    echo 错误: Python路径不存在!
    pause
    exit /b 1
)

echo 路径存在 ✓
echo.

echo 正在修复环境变量...
echo.

echo 1. 更新用户级环境变量
setx PATH "%PYTHON_PATH%;%SCRIPTS_PATH%;%PATH%"

echo.
echo 2. 更新系统级环境变量
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH /t REG_EXPAND_SZ /d "%PYTHON_PATH%;%SCRIPTS_PATH%;%PATH%" /f

echo.
echo ==============================================
echo 配置完成!
echo.
echo 请关闭所有终端窗口并重新打开
echo 然后执行以下命令验证:
echo   python --version
echo   pip --version
echo ==============================================
pause