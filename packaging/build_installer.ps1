# build_installer.ps1
# Builds Streamore Monitor Windows installer using PyInstaller + Inno Setup
#
# Usage:
#   .\packaging\build_installer.ps1
#   .\packaging\build_installer.ps1 -SkipPyInstaller             # skip PyInstaller rebuild
#   .\packaging\build_installer.ps1 -PrevVersion 1.0.11          # also generate delta patch
#
# Requirements:
#   - Inno Setup 6+ installed (https://jrsoftware.org/isdl.php)
#   - Python venv at .\venv\ or .\env\
#   - PyInstaller in the venv

param(
    [switch]$SkipPyInstaller,
    [string]$PrevVersion = "",    # Set to generate a delta patch ZIP (e.g. "1.0.11")
    [switch]$SkipUpload           # Pass to skip automatic GitHub release upload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "=== Streamore Monitor Installer Build ===" -ForegroundColor Cyan
Write-Host "Working directory: $Root"

# ── 1. Locate Python venv ─────────────────────────────────────────────────────
$PythonExe = $null
foreach ($candidate in @("$Root\.venv\Scripts\python.exe", "$Root\venv\Scripts\python.exe", "$Root\env\Scripts\python.exe")) {
    if (Test-Path $candidate) { $PythonExe = $candidate; break }
}
if (-not $PythonExe) {
    $PythonExe = Get-Command "python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}
if (-not $PythonExe) {
    Write-Error "Could not find any Python interpreter (venv or system)."
    exit 1
}
Write-Host "Python: $PythonExe" -ForegroundColor Green

# ── 2. Locate Inno Setup ISCC.exe ─────────────────────────────────────────────
$IsccExe = $null
$IssSearchPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
)
foreach ($path in $IssSearchPaths) {
    if (Test-Path $path) { $IsccExe = $path; break }
}
# Also try PATH
if (-not $IsccExe) {
    $IsccExe = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}
if (-not $IsccExe) {
    Write-Host ""
    Write-Host "Inno Setup not found. Please install it from:" -ForegroundColor Yellow
    Write-Host "  https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then re-run this script." -ForegroundColor Yellow
    exit 1
}
Write-Host "Inno Setup ISCC: $IsccExe" -ForegroundColor Green

# ── 3. Get version from shared/version.py ─────────────────────────────────────
$VersionFile = "$Root\shared\version.py"
$Version = (Get-Content $VersionFile | Select-String '__version__\s*=\s*"(.+)"').Matches.Groups[1].Value
if (-not $Version) { $Version = "1.0.0" }
Write-Host "Version: $Version" -ForegroundColor Green

# ── 4. Build exe with PyInstaller ─────────────────────────────────────────────
if (-not $SkipPyInstaller) {
    Write-Host ""
    Write-Host "── Building exe with PyInstaller ──" -ForegroundColor Cyan
    Push-Location $Root
    & $PythonExe -m PyInstaller packaging\pyinstaller.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }
    Pop-Location
    Write-Host "PyInstaller build complete." -ForegroundColor Green
} else {
    Write-Host "Skipping PyInstaller build (-SkipPyInstaller)." -ForegroundColor Yellow
}

# Verify exe exists
$ExePath = "$Root\dist\StreamoreMonitor\StreamoreMonitor.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "StreamoreMonitor.exe not found at $ExePath. Run without -SkipPyInstaller."
    exit 1
}
$ExeSize = [math]::Round((Get-Item $ExePath).Length / 1MB, 1)
Write-Host "Exe: $ExePath ($ExeSize MB)" -ForegroundColor Green

# ── 5. Build installer with Inno Setup ───────────────────────────────────────
Write-Host ""
Write-Host "── Building installer with Inno Setup ──" -ForegroundColor Cyan

$IssFile = "$Root\packaging\installer.iss"

# Update AppVersion in the .iss file dynamically via /D define overrides
& $IsccExe `
    "/DAppVersion=$Version" `
    $IssFile

if ($LASTEXITCODE -ne 0) { Write-Error "Inno Setup build failed"; exit 1 }

# ── 6. Output result ─────────────────────────────────────────────────────────
$SetupExe = "$Root\dist\StreamoreMonitor-$Version-Setup.exe"
if (Test-Path $SetupExe) {
    $SetupSize = [math]::Round((Get-Item $SetupExe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "=== Installer ready ===" -ForegroundColor Green
    Write-Host "  $SetupExe ($SetupSize MB)" -ForegroundColor Green
    Write-Host ""
    if (-not $SkipUpload) {
        Write-Host ""
        Write-Host "── Uploading installer to GitHub release v$Version ──" -ForegroundColor Cyan
        gh release upload "v$Version" "$SetupExe" --repo younglotushuncho/moviedownloader --clobber
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Installer uploaded." -ForegroundColor Green
        } else {
            Write-Host "  [warn] Installer upload failed (exit $LASTEXITCODE)" -ForegroundColor Yellow
        }
        # Always upload manifest.hmac so ALL installed client versions can fetch the HMAC key
        $HmacFile = Join-Path $Root "manifest.hmac"
        if (Test-Path $HmacFile) {
            gh release upload "v$Version" "$HmacFile" --repo younglotushuncho/moviedownloader --clobber
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  manifest.hmac uploaded." -ForegroundColor Green
            } else {
                Write-Host "  [warn] manifest.hmac upload failed" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "Upload to GitHub release:" -ForegroundColor Cyan
        Write-Host "  gh release upload v$Version `"dist\StreamoreMonitor-$Version-Setup.exe`" --repo younglotushuncho/moviedownloader --clobber"
    }
} else {
    Write-Error "Expected installer not found: $SetupExe"
    exit 1
}

# ── 7. Generate delta patch ZIP (optional) ────────────────────────────────────
if ($PrevVersion -ne "") {
    Write-Host ""
    Write-Host "── Generating delta patch from v$PrevVersion → v$Version ──" -ForegroundColor Cyan
    & $PythonExe "$Root\scripts\generate_patch.py" --version $Version --prev-version $PrevVersion
    if ($LASTEXITCODE -eq 0) {
        $PatchFile = "$Root\packaging\dist\patch_v$Version.zip"
        if (Test-Path $PatchFile) {
            $PatchSize = [math]::Round((Get-Item $PatchFile).Length / 1KB, 1)
            Write-Host ""
            Write-Host "=== Patch ready ($PatchSize KB - much smaller than the full installer!) ===" -ForegroundColor Green
            Write-Host "  $PatchFile" -ForegroundColor Green
            Write-Host ""
            if (-not $SkipUpload) {
                Write-Host "── Uploading patch assets to GitHub release v$Version ──" -ForegroundColor Cyan
                gh release upload "v$Version" "$PatchFile" --repo younglotushuncho/moviedownloader --clobber
                if ($LASTEXITCODE -eq 0) { Write-Host "  patch ZIP uploaded." -ForegroundColor Green } else { Write-Host "  [warn] patch upload failed" -ForegroundColor Yellow }
                gh release upload "v$Version" "$Root\manifest.signed.json" --repo younglotushuncho/moviedownloader --clobber
                if ($LASTEXITCODE -eq 0) { Write-Host "  manifest.signed.json uploaded." -ForegroundColor Green } else { Write-Host "  [warn] manifest upload failed" -ForegroundColor Yellow }
                $HmacFile = Join-Path $Root "manifest.hmac"
                if (Test-Path $HmacFile) {
                    gh release upload "v$Version" "$HmacFile" --repo younglotushuncho/moviedownloader --clobber
                    if ($LASTEXITCODE -eq 0) { Write-Host "  manifest.hmac uploaded." -ForegroundColor Green } else { Write-Host "  [warn] manifest.hmac upload failed" -ForegroundColor Yellow }
                }
            } else {
                Write-Host "Upload patch + updated manifest:" -ForegroundColor Cyan
                Write-Host "  gh release upload v$Version `"packaging\dist\patch_v$Version.zip`" --repo younglotushuncho/moviedownloader --clobber"
                Write-Host "  gh release upload v$Version `"manifest.signed.json`" --repo younglotushuncho/moviedownloader --clobber"
            }
        }
    } else {
        Write-Host "[warn] Patch generation failed (non-critical)" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host 'Tip: run with -PrevVersion <last_version> to also generate a delta patch ZIP.' -ForegroundColor DarkGray
    Write-Host '  Example: .\packaging\build_installer.ps1 -PrevVersion ' + ($([int]($Version.Split('.')[-1]) - 1).ToString()) -ForegroundColor DarkGray
}
