@echo off
REM Complete startup script - starts both backend and frontend

echo ====================================
echo  YTS Movie Monitor - Full Startup
echo ====================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Backend API...
start "YTS Backend" cmd /k "python backend/app.py"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend UI...
start "YTS Frontend" cmd /k "python frontend/main.py"

echo.
echo ====================================
echo  Both services started!
echo  Backend: http://127.0.0.1:5000
echo  Frontend: Desktop app window
echo ====================================
echo.
echo Close this window or press any key...
pause >nul
