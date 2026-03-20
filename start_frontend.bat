@echo off
REM Start Frontend Script for YTS Movie Monitor

echo Starting YTS Movie Monitor Frontend...
echo.
echo Make sure the backend is running first!
echo (Run start_backend.bat in another window)
echo.

cd /d "%~dp0"
python frontend/main.py

pause
