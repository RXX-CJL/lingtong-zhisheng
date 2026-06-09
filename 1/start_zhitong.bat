@echo off
chcp 65001 > nul
echo ================================================
echo       智瞳灵声 - 智慧交管系统启动
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python或环境变量未配置
    echo 请确保Python已正确安装并添加到PATH环境变量
    pause
    exit /b 1
)
echo ✓ Python环境检测成功

echo.
echo [2/3] 检查项目文件...
if not exist "zhitong\main.py" (
    echo 错误: 找不到项目文件
    pause
    exit /b 1
)
echo ✓ 项目文件完整

echo.
echo [3/3] 启动系统...
echo.

python zhitong\main.py

echo.
echo 系统已退出
pause
