@echo off
echo Renaming aria2c.tmp to aria2c.exe...
echo.
echo This requires Windows Defender real-time protection to be temporarily disabled,
echo OR adding this folder to Windows Defender exclusions.
echo.
echo Current folder: %CD%\bin
echo.
pause

cd /d "%~dp0"
if exist "bin\aria2c.tmp" (
    ren "bin\aria2c.tmp" "aria2c.exe"
    if exist "bin\aria2c.exe" (
        echo.
        echo SUCCESS: aria2c.exe created successfully!
        echo.
        echo Testing aria2...
        bin\aria2c.exe --version        echo.
        echo Done! You can now restart the backend and it will use aria2.
    ) else (
        echo.
        echo ERROR: Failed to rename. Windows Defender may be blocking the operation.
        echo.
        echo Please add this folder to Windows Defender exclusions:
        echo %CD%\bin
        echo.
        echo Then run this script again.
    )
) else (
    echo ERROR: bin\aria2c.tmp not found!
)

pause
