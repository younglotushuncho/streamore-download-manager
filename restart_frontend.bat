@echo off
REM Restart Frontend with New Features

echo ====================================
echo  Restarting Frontend with Updates
echo ====================================
echo.
echo Changes:
echo   - Real poster images displayed
echo   - Better image scaling
echo   - Improved UI
echo.
echo Close the old window and this will start a new one...
echo.

cd /d "%~dp0"
python restart_frontend.py

pause
