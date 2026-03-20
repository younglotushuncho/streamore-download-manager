param(
  [string]$InstallerPath = "desktop/Output/StreamoreSetup.exe",
  [string]$Version = "",
  [string]$MinimumRequiredVersion = "",
  [switch]$SkipPostVerify,
  [string]$R2PublicBaseUrl = $env:R2_PUBLIC_BASE_URL,
  [string]$Bucket = $env:R2_BUCKET,
  [string]$AccountId = $env:R2_ACCOUNT_ID,
  [string]$AccessKeyId = $env:R2_ACCESS_KEY_ID,
  [string]$SecretAccessKey = $env:R2_SECRET_ACCESS_KEY
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InstallerPath)) {
  throw "Installer not found: $InstallerPath"
}

if (-not $Version) {
  $ver = (Get-Content shared/version.py | Select-String '__version__\s*=\s*"(.+)"').Matches.Groups[1].Value
  if (-not $ver) { $ver = "0.0.0" }
  $Version = $ver
}

if (-not $MinimumRequiredVersion) {
  $MinimumRequiredVersion = $Version
}

if (-not $R2PublicBaseUrl) { throw "Missing R2_PUBLIC_BASE_URL" }
if (-not $Bucket) { throw "Missing R2_BUCKET" }
if (-not $AccountId) { throw "Missing R2_ACCOUNT_ID" }
if (-not $AccessKeyId) { throw "Missing R2_ACCESS_KEY_ID" }
if (-not $SecretAccessKey) { throw "Missing R2_SECRET_ACCESS_KEY" }

$base = $R2PublicBaseUrl.TrimEnd('/')
$url = "$base/StreamoreSetup.exe"
$sha = (Get-FileHash $InstallerPath -Algorithm SHA256).Hash
$appExePath = Join-Path (Split-Path -Parent $InstallerPath) "StreamoreManager\StreamoreManager.exe"
$appSha = ""
if (Test-Path $appExePath) {
  $appSha = (Get-FileHash $appExePath -Algorithm SHA256).Hash
}

$latestPath = Join-Path (Split-Path -Parent $InstallerPath) "latest.json"
$payload = @{
  version = $Version
  minimum_required_version = $MinimumRequiredVersion
  download_url = $url
  sha256 = $sha
  app_sha256 = $appSha
  published_at = (Get-Date).ToString("o")
} | ConvertTo-Json -Depth 3

# Write UTF-8 without BOM to avoid JSON parser issues in clients.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($latestPath, $payload, $utf8NoBom)
if (-not (Test-Path $latestPath)) { throw "latest.json not created: $latestPath" }

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
  throw "aws CLI not found. Install it and retry."
}

$endpoint = "https://$AccountId.r2.cloudflarestorage.com"
$env:AWS_ACCESS_KEY_ID = $AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $SecretAccessKey
$env:AWS_DEFAULT_REGION = "auto"

aws s3 cp $InstallerPath "s3://$Bucket/StreamoreSetup.exe" --endpoint-url $endpoint
if ($LASTEXITCODE -ne 0) { throw "Failed to upload installer to R2" }
aws s3 cp $latestPath "s3://$Bucket/latest.json" --endpoint-url $endpoint --cache-control "no-cache"
if ($LASTEXITCODE -ne 0) { throw "Failed to upload latest.json to R2" }

if (-not $SkipPostVerify) {
  & .\packaging\verify_r2_release.ps1 -BaseUrl $base
}

Write-Output "Uploaded to R2: $url"
Write-Output "latest.json: $base/latest.json"
Write-Output "minimum_required_version: $MinimumRequiredVersion"
if ($appSha) {
  Write-Output "app_sha256: $appSha"
}
