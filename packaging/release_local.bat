@echo off
setlocal

REM Streamore local build + publish
powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'F:\Softwares\projects\movie project'; .\packaging\publish_r2.ps1 -InstallerPath "F:\Softwares\projects\movie project\desktop\Output\StreamoreSetup.exe""

if %errorlevel% neq 0 (
  echo.
  echo Build or publish failed. See output above.
  pause
  exit /b %errorlevel%
)

echo.
echo Build and publish completed.
pause

