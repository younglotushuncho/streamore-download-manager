<#!
Build script – Streamore Desktop Download Manager (Nuitka)
==================================================
Builds a qBittorrent-style desktop download manager as a single installer,
using Nuitka instead of PyInstaller to avoid Antivirus false positives.

Prerequisites:
  - Activate your virtualenv
  - pip install nuitka
  - bin/aria2c.exe must exist

Usage:
    .\packaging\build_nuitka.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# --- Avoid UNC/long-path issues by re-invoking from a subst drive ---
function Get-FreeDriveLetter {
    foreach ($c in @('Z','Y','X','W','V','U','T')) {
        if (-not (Get-PSDrive -Name $c -ErrorAction SilentlyContinue)) {
            return $c
        }
    }
    return $null
}

function Normalize-LongPath([string]$p) {
    if ($p -like '\\?\*') { return $p.Substring(4) }
    return $p
}

if (-not $env:STREAMORE_SUBST_DONE) {
    $repoRoot = Normalize-LongPath (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $drive = Get-FreeDriveLetter
    if ($drive) {
        $drivePath = "$drive`:"
        cmd /c "subst $drivePath `"$repoRoot`"" | Out-Null
        $env:STREAMORE_SUBST_DONE = '1'
        & "$drivePath\packaging\build_nuitka.ps1"
        $exitCode = $LASTEXITCODE
        cmd /c "subst $drivePath /d" | Out-Null
        exit $exitCode
    } else {
        Write-Warning "No free drive letter found to work around path issues."
    }
}

# --- Short temp/cache paths to avoid GCC failures ---
$shortTemp = 'C:\Temp'
$shortCache = 'C:\nuitka_cache'
foreach ($p in @($shortTemp, $shortCache)) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}
$env:TEMP = $shortTemp
$env:TMP = $shortTemp
$env:NUITKA_TMP_DIR = $shortTemp
$env:NUITKA_CACHE_DIR = $shortCache

# 1. Install requirements
Write-Host "Installing Nuitka and dependencies..." -ForegroundColor Cyan
pip install -r backend\requirements.txt --disable-pip-version-check -q
pip install -r desktop\requirements.txt --disable-pip-version-check -q
pip install nuitka --disable-pip-version-check -q

# 2. Clean old builds
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
Stop-Process -Name "StreamoreManager" -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist\downloader_app.build
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist\downloader_app.dist
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist\StreamoreManager

# Keep installer/app version aligned with shared/version.py
$Version = (Get-Content shared/version.py | Select-String '__version__\s*=\s*"(.+)"').Matches.Groups[1].Value
if (-not $Version) { $Version = "1.0.0" }
Write-Host "Version: $Version" -ForegroundColor Cyan

# 3. Build using Nuitka
Write-Host "Compiling Streamore Download Manager to C with Nuitka..." -ForegroundColor Green
Write-Host "Note: This can take 15-30 minutes. LTO=yes is forced to avoid Windows linker limits." -ForegroundColor Yellow

$env:NUITKA_ASSUME_YES_FOR_DOWNLOADS="yes"

# NOTE: --lto=yes is REQUIRED here.
# Without it, Nuitka passes 698+ individual .o files to ld.exe which exceeds
# Windows' command-line length limit and crashes with no error message.
# (Nuitka logs: "LTO mode auto was resolved to 'no'... force it with '--lto=yes'")
#
# We also exclude PIL image format plugins we don't use to reduce module count.

python -m nuitka --standalone --mingw64 `
    --assume-yes-for-downloads `
    --windows-console-mode=disable `
    --output-dir="dist" `
    --windows-icon-from-ico="desktop\icon.ico" `
    --enable-plugin=pyqt6 `
    --include-data-dir="bin=bin" `
    --include-package="backend" `
    --include-package="shared" `
    --include-module="sqlite3" `
    --include-module="engineio.async_drivers.threading" `
    --include-module="flask_socketio" `
    --include-module="flask_cors" `
    --include-module="simple_websocket" `
    --include-module="pystray._win32" `
    --include-module="PIL._tkinter_finder" `
    --include-module="plyer.platforms.win.notification" `
    --include-module="curl_cffi" `
    --include-module="bs4" `
    --nofollow-import-to="PIL.BlpImagePlugin" `
    --nofollow-import-to="PIL.BufrStubImagePlugin" `
    --nofollow-import-to="PIL.CurImagePlugin" `
    --nofollow-import-to="PIL.DcxImagePlugin" `
    --nofollow-import-to="PIL.DdsImagePlugin" `
    --nofollow-import-to="PIL.EpsImagePlugin" `
    --nofollow-import-to="PIL.FliImagePlugin" `
    --nofollow-import-to="PIL.FpxImagePlugin" `
    --nofollow-import-to="PIL.FtexImagePlugin" `
    --nofollow-import-to="PIL.GbrImagePlugin" `
    --nofollow-import-to="PIL.GribStubImagePlugin" `
    --nofollow-import-to="PIL.Hdf5StubImagePlugin" `
    --nofollow-import-to="PIL.IcnsImagePlugin" `
    --nofollow-import-to="PIL.ImtImagePlugin" `
    --nofollow-import-to="PIL.IptcImagePlugin" `
    --nofollow-import-to="PIL.McIdasImagePlugin" `
    --nofollow-import-to="PIL.MicImagePlugin" `
    --nofollow-import-to="PIL.MpegImagePlugin" `
    --nofollow-import-to="PIL.MspImagePlugin" `
    --nofollow-import-to="PIL.PalmImagePlugin" `
    --nofollow-import-to="PIL.PcdImagePlugin" `
    --nofollow-import-to="PIL.PdfImagePlugin" `
    --nofollow-import-to="PIL.PixarImagePlugin" `
    --nofollow-import-to="PIL.SgiImagePlugin" `
    --nofollow-import-to="PIL.SpiderImagePlugin" `
    --nofollow-import-to="PIL.SunImagePlugin" `
    --nofollow-import-to="PIL.TgaImagePlugin" `
    --nofollow-import-to="PIL.WmfImagePlugin" `
    --nofollow-import-to="PIL.XVThumbImagePlugin" `
    --nofollow-import-to="PIL.XbmImagePlugin" `
    --nofollow-import-to="PIL.XpmImagePlugin" `
    --lto=yes `
    --output-filename="StreamoreManager.exe" `
    --jobs=4 `
    desktop\downloader_app.py

if ($LASTEXITCODE -ne 0) {
    throw "Nuitka build failed with exit code $LASTEXITCODE"
}

Write-Host "" 
Write-Host "Verifying and cleaning up Nuitka output..." -ForegroundColor Cyan
# Nuitka names the dist folder as <script_basename>.dist
$distFolder = "dist\downloader_app.dist"
if (Test-Path $distFolder) {
    $target = "dist\StreamoreManager"
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Rename-Item $distFolder "StreamoreManager"
    Write-Host "Renamed $distFolder -> dist\StreamoreManager" -ForegroundColor Green
} else {
    Write-Host "WARNING: Expected dist folder '$distFolder' not found." -ForegroundColor Yellow
    Get-ChildItem dist\ | Where-Object { $_.PSIsContainer } | Select-Object Name
}

# Ensure aria2 binary is bundled into app output (explicit copy for reliability).
$sourceAria2 = "bin\aria2c.exe"
if (-not (Test-Path $sourceAria2)) {
    throw "Required aria2 binary missing in repo: $sourceAria2"
}
$targetBinDir = "dist\StreamoreManager\bin"
if (-not (Test-Path $targetBinDir)) {
    New-Item -ItemType Directory -Path $targetBinDir | Out-Null
}
Copy-Item -Force $sourceAria2 (Join-Path $targetBinDir "aria2c.exe")
if (-not (Test-Path (Join-Path $targetBinDir "aria2c.exe"))) {
    throw "Failed to bundle aria2 into dist output"
}

Write-Host "" 
Write-Host "Building installer with Inno Setup..." -ForegroundColor Cyan
$iscc = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "Inno Setup not found: $iscc"
}
& $iscc "/DAppVersion=$Version" packaging\installer.iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

# Always build from repository root so relative paths resolve consistently.
$RepoRootResolved = Normalize-LongPath (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRootResolved
if (-not (Test-Path "dist\StreamoreSetup.exe")) {
    throw "Installer build failed: dist\StreamoreSetup.exe not found"
}

Write-Host ""
Write-Host "Running release smoke checks..." -ForegroundColor Cyan
& .\packaging\smoke_release.ps1 -InstallerPath "dist\StreamoreSetup.exe" -AppExePath "dist\StreamoreManager\StreamoreManager.exe" -Aria2Path "dist\StreamoreManager\bin\aria2c.exe" -ExpectedVersion $Version

Write-Host "" 
Write-Host "Publishing to R2..." -ForegroundColor Cyan
& .\packaging\publish_r2.ps1 -InstallerPath "dist\StreamoreSetup.exe" -Version $Version -MinimumRequiredVersion $Version

Write-Host "" 
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "  App -> dist\StreamoreManager\StreamoreManager.exe" -ForegroundColor Green
Write-Host "  Installer -> dist\StreamoreSetup.exe" -ForegroundColor Green


