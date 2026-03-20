<#
Build script – Streamore Desktop Download Manager
==================================================
Builds a qBittorrent-style desktop download manager as a single installer.

Prerequisites:
  - Activate your virtualenv
  - pip install pyinstaller
  - bin/aria2c.exe must exist (or be on PATH)

Usage:
    .\packaging\build_backend.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# 1. Install requirements
Write-Host "Installing Python requirements..." -ForegroundColor Cyan
pip install -r backend\requirements.txt --disable-pip-version-check -q
pip install -r desktop\requirements.txt --disable-pip-version-check -q
pip install pyinstaller --disable-pip-version-check -q

# 2. Clean old builds
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist

# 3. Build the all-in-one Download Manager desktop app (qBittorrent style)
#    This bundles both the PyQt6 GUI AND the Flask backend in ONE exe.
Write-Host "Building Streamore Download Manager (desktop app)..." -ForegroundColor Green
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
