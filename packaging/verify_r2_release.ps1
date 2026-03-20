param(
  [string]$BaseUrl = $env:R2_PUBLIC_BASE_URL,
  [int]$TimeoutSec = 60
)

$ErrorActionPreference = "Stop"

if (-not $BaseUrl) { throw "Missing R2 base URL (R2_PUBLIC_BASE_URL)" }
$base = $BaseUrl.TrimEnd('/')
$latestUrl = "$base/latest.json"

Write-Host "Verifying R2 release..." -ForegroundColor Cyan
Write-Host "  latest.json: $latestUrl"

try {
  $resp = Invoke-WebRequest -UseBasicParsing -Uri $latestUrl -TimeoutSec $TimeoutSec
} catch {
  throw "Failed to fetch latest.json: $($_.Exception.Message)"
}

if ($resp.StatusCode -ne 200) {
  throw "latest.json HTTP status $($resp.StatusCode)"
}

try {
  $latest = $resp.Content | ConvertFrom-Json
} catch {
  throw "latest.json is not valid JSON"
}

foreach($required in @("version","minimum_required_version","download_url","sha256","published_at")) {
  if (-not $latest.PSObject.Properties.Name.Contains($required)) {
    throw "latest.json missing required field '$required'"
  }
}

$downloadUrl = [string]$latest.download_url
if ([string]::IsNullOrWhiteSpace($downloadUrl)) {
  throw "latest.json download_url is empty"
}

try {
  $tmpFile = Join-Path ([System.IO.Path]::GetTempPath()) ("streamore-installer-" + [guid]::NewGuid().ToString("N") + ".exe")
  Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $tmpFile -TimeoutSec $TimeoutSec
  $hash = (Get-FileHash $tmpFile -Algorithm SHA256).Hash
  if (($hash.ToUpperInvariant()) -ne ([string]$latest.sha256).ToUpperInvariant()) {
    throw "SHA mismatch. latest.json=$($latest.sha256) actual=$hash"
  }
  $size = (Get-Item $tmpFile).Length
  if ($size -lt 20000000) {
    throw "Installer downloaded but suspiciously small: $size bytes"
  }
} finally {
  if ($tmpFile -and (Test-Path $tmpFile)) {
    Remove-Item -Force $tmpFile -ErrorAction SilentlyContinue
  }
}

Write-Host "R2 verification passed." -ForegroundColor Green
Write-Host "  version: $($latest.version)"
Write-Host "  minimum_required_version: $($latest.minimum_required_version)"
Write-Host "  download_url: $downloadUrl"

