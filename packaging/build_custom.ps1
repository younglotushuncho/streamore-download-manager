<#
Build script – Streamore Desktop Download Manager (Custom Bootloader)
==================================================
Builds a qBittorrent-style desktop download manager as a single installer.
This script compiles a CUSTOM PyInstaller bootloader to bypass Antivirus False Positives.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# 1. Install requirements
Write-Host "Installing Python requirements..." -ForegroundColor Cyan
pip install -r backend\requirements.txt --disable-pip-version-check -q
pip install -r desktop\requirements.txt --disable-pip-version-check -q
pip install wheel --disable-pip-version-check -q

# 2. Build Custom PyInstaller Bootloader
Write-Host "Re-compiling PyInstaller from scratch to bypass AVG False Positives..." -ForegroundColor Yellow
$pyinstaller_dir = "packaging\pyinstaller-source"
if (-not (Test-Path $pyinstaller_dir)) {
    # Download PyInstaller source
    Write-Host "Downloading PyInstaller source..."
    git clone https://github.com/pyinstaller/pyinstaller.git $pyinstaller_dir -q
}

Push-Location $pyinstaller_dir
git checkout v6.4.0 -q
Push-Location bootloader

# Find GCC if it exists (for local PC), else fallback to default compiler (e.g. MSVC on GitHub Actions)
$gcc_path = "$env:LOCALAPPDATA\Nuitka\Nuitka\Cache\downloads\gcc"
if (Test-Path $gcc_path) {
    $gcc_bin = Get-ChildItem -Path $gcc_path -Filter "gcc.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gcc_bin) {
        $gcc_dir = $gcc_bin.Directory.FullName
        $env:PATH = "$gcc_dir;$env:PATH"
        Write-Host "Compiling custom bootloader using GCC at: $gcc_dir"
    }
} else {
    Write-Host "Compiling custom bootloader using default CI compiler (MSVC/GCC)..."
}
python ./waf all
Pop-Location

Write-Host "Installing our custom PyInstaller..."
pip install . --disable-pip-version-check -q
Pop-Location

# 3. Clean old builds
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist

# 4. Build the all-in-one Download Manager
Write-Host "Building Streamore Download Manager..." -ForegroundColor Green
pyinstaller --noconfirm --clean --onedir `
    --windowed `
    --name "StreamoreManager" `
    --icon "desktop\icon.ico" `
    --add-data "bin;bin" `
    --add-data "backend;backend" `
    --add-data "shared;shared" `
    --hidden-import sqlite3 `
    --hidden-import _sqlite3 `
    --collect-all sqlite3 `
    --hidden-import PyQt6.QtWidgets `
    --hidden-import PyQt6.QtCore `
    --hidden-import PyQt6.QtGui `
    --hidden-import PyQt6.QtNetwork `
    --hidden-import engineio.async_drivers.threading `
    --hidden-import flask_socketio `
    --hidden-import flask_cors `
    --hidden-import simple_websocket `
    --hidden-import pystray._win32 `
    --hidden-import PIL._tkinter_finder `
    --hidden-import plyer.platforms.win.notification `
    --hidden-import curl_cffi `
    --hidden-import bs4 `
    --exclude-module tkinter `
    --exclude-module _tkinter `
    desktop\downloader_app.py

Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "  App -> dist\StreamoreManager\" -ForegroundColor Green
Write-Host ""
Write-Host "Next: compile the installer:"
Write-Host "  ISCC.exe packaging\installer.iss"
