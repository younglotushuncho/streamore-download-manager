param(
  [string]$InstallerPath = "dist/StreamoreSetup.exe",
  [string]$AppExePath = "dist/StreamoreManager/StreamoreManager.exe",
  [string]$Aria2Path = "dist/StreamoreManager/bin/aria2c.exe",
  [string]$LatestPath = "dist/latest.json",
  [string]$ExpectedVersion = ""
)

$ErrorActionPreference = "Stop"

function Assert-Exists([string]$PathValue, [string]$Label) {
  if (-not (Test-Path $PathValue)) {
    throw "$Label missing: $PathValue"
  }
}

function Assert-MinBytes([string]$PathValue, [int64]$MinBytes, [string]$Label) {
  $size = (Get-Item $PathValue).Length
  if ($size -lt $MinBytes) {
    throw "$Label too small: $PathValue ($size bytes)"
  }
  return $size
}

Write-Host "Running local release smoke checks..." -ForegroundColor Cyan

Assert-Exists $InstallerPath "Installer"
Assert-Exists $AppExePath "App executable"
Assert-Exists $Aria2Path "aria2 binary"

$installerSize = Assert-MinBytes $InstallerPath 20000000 "Installer"
$appSize = Assert-MinBytes $AppExePath 8000000 "App executable"
$aria2Size = Assert-MinBytes $Aria2Path 1000000 "aria2 binary"

$ver = (Get-Content shared/version.py | Select-String '__version__\s*=\s*"(.+)"').Matches.Groups[1].Value
if (-not $ver) { $ver = "0.0.0" }
if ($ExpectedVersion -and $ExpectedVersion -ne $ver) {
  throw "Version mismatch: expected '$ExpectedVersion' but shared/version.py is '$ver'"
}

if (Test-Path $LatestPath) {
  try {
    $latest = Get-Content $LatestPath -Raw | ConvertFrom-Json
  } catch {
    throw "latest.json exists but is not valid JSON: $LatestPath"
  }
  foreach($required in @("version","minimum_required_version","download_url","sha256","published_at")) {
    if (-not $latest.PSObject.Properties.Name.Contains($required)) {
      throw "latest.json missing required field '$required'"
    }
  }
}

Write-Host "Smoke checks passed." -ForegroundColor Green
Write-Host "  Version: $ver"
Write-Host "  Installer size: $installerSize bytes"
Write-Host "  App size: $appSize bytes"
Write-Host "  aria2 size: $aria2Size bytes"

