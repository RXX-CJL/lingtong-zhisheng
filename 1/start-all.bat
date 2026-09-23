@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =========================================
echo   ZhiTong LingSheng - Dev Env Start
echo   Project Dir: %~dp0
echo =========================================
echo.

echo [1/3] Starting Backend API (Port 8001)...
cd api
start "ZhiTong Backend API" cmd /k cd /d %~dp0api ^&^& py -3 -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
cd ..
echo   Backend started, waiting 4 seconds...
timeout /t 4 /nobreak >nul
echo.

echo [2/3] Starting Web Admin (Port 5173)...
cd web-admin
start "ZhiTong Web Admin" cmd /k cd /d %~dp0web-admin ^&^& npm run dev
cd ..
echo   Frontend started, waiting 5 seconds...
timeout /t 5 /nobreak >nul
echo.

echo [3/3] Opening browser...
echo =========================================
echo   Startup Complete!
echo   - API Docs:    http://127.0.0.1:8001/docs
echo   - Web Admin:   http://localhost:5173
echo =========================================
echo.
echo Tips:
echo   - Do not close the two black windows
echo   - To stop services, close the windows
echo   - If a window flashes and disappears, check the command manually
echo.
start http://localhost:5173
pause