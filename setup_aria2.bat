@echo off
echo ==================================
echo   aria2 Setup for Windows
echo ==================================
echo.

set "BIN_DIR=%~dp0bin"
set "ARIA2_EXE=%BIN_DIR%\aria2c.exe"

REM Check if aria2 is already installed
if exist "%ARIA2_EXE%" (
    echo aria2c.exe already exists at: %ARIA2_EXE%
    echo.
    set /p overwrite="Do you want to re-download? (y/N): "
    if /i not "%overwrite%"=="y" (
        echo Setup cancelled.
        exit /b 0
    )
)

REM Create bin directory if it doesn't exist
if not exist "%BIN_DIR%" (
    echo Creating bin directory...
    mkdir "%BIN_DIR%"
)

REM Download using curl (built into Windows 10+)
set "ARIA2_VERSION=1.37.0"
set "DOWNLOAD_URL=https://github.com/aria2/aria2/releases/download/release-%ARIA2_VERSION%/aria2-%ARIA2_VERSION%-win-64bit-build1.zip"
set "ZIP_FILE=%TEMP%\aria2.zip"
set "EXTRACT_DIR=%TEMP%\aria2_extract"

echo Downloading aria2 v%ARIA2_VERSION%...
echo URL: %DOWNLOAD_URL%
echo.

curl -L "%DOWNLOAD_URL%" -o "%ZIP_FILE%"
if errorlevel 1 (
    echo Error downloading aria2
    exit /b 1
)

echo Download complete
echo.

REM Extract using PowerShell
echo Extracting archive...
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%EXTRACT_DIR%' -Force"

REM Find and copy aria2c.exe
echo Installing aria2c.exe to bin directory...
for /r "%EXTRACT_DIR%" %%F in (aria2c.exe) do (
    copy "%%F" "%ARIA2_EXE%" >nul
    goto :found
)

echo Error: aria2c.exe not found in downloaded archive
exit /b 1

:found
echo Installation complete
echo.

REM Clean up
echo Cleaning up temporary files...
del "%ZIP_FILE%" 2>nul
rmdir /s /q "%EXTRACT_DIR%" 2>nul

echo.
echo ==================================
echo   Setup Complete!
echo ==================================
echo.
echo aria2c.exe installed at:
echo   %ARIA2_EXE%
echo.

REM Verify installation
echo Verifying installation...
"%ARIA2_EXE%" --version | findstr /C:"aria2"

echo.
echo Next Steps:
echo   1. Restart the backend server (if running)
echo      Press Ctrl+C in the backend terminal, then run:
echo      python -m backend.app
echo.
echo   2. Test a download from the frontend UI
echo      - Click on a movie card
echo      - Click Download for your preferred quality
echo      - Check the Downloads tab to see progress
echo.
echo   3. (Optional) Set RPC secret for security:
echo      set ARIA2_RPC_SECRET=your-secret-token
echo.

pause
