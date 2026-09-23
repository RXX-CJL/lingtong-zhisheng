@echo off
chcp 65001
echo =========================================
echo 智瞳智慧交管系统API服务启动
echo =========================================
echo.

cd /d "%~dp0"

set PYTHON=C:\miniconda\envs\zhitong-gpu\python.exe
set PIP=C:\miniconda\envs\zhitong-gpu\Scripts\pip.exe

echo [1/3] 检查Python环境...
%PYTHON% --version
if errorlevel 1 (
    echo 错误: 未找到zhitong-gpu环境
    pause
    exit /b 1
)

echo.
echo [2/3] 检查依赖包...
%PIP% show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    %PIP% install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
)

echo.
echo [3/3] 启动API服务...
echo 服务地址: http://localhost:8001
echo API文档: http://localhost:8001/docs
echo.
echo 按 Ctrl+C 停止服务
echo =========================================
echo.

%PYTHON% app.py

pause