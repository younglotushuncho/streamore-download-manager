@echo off
echo ====================================
echo YTS Movie Monitor - Restart Script
echo ====================================
echo.
echo This will:
echo 1. Stop any running backend/frontend
echo 2. Start backend server
echo 3. Start frontend GUI
echo.
pause

echo.
echo Stopping existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *backend*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *frontend*" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting backend server...
start "Backend Server" cmd /k "cd /d %~dp0 && python -m backend.app"
timeout /t 3 /nobreak >nul

echo.
echo Starting frontend GUI...
start "Frontend GUI" cmd /k "cd /d %~dp0 && python -m frontend.main"

echo.
echo Both services started!
echo - Backend: http://127.0.0.1:5000
echo - Frontend: GUI window should appear
echo.
echo Close this window or press any key to exit...
pause >nul
