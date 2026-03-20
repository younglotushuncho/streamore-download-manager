@echo off
REM Start Backend Script for YTS Movie Monitor

echo Starting YTS Movie Monitor Backend...
echo.

cd /d "%~dp0"
python backend/app.py

pause
