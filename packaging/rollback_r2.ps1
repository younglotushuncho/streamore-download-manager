param(
  [Parameter(Mandatory=$true)][string]$Version,
  [Parameter(Mandatory=$true)][string]$DownloadUrl,
  [Parameter(Mandatory=$true)][string]$Sha256,
  [string]$AppSha256 = "",
  [string]$MinimumRequiredVersion = "",
  [string]$Bucket = $env:R2_BUCKET,
  [string]$AccountId = $env:R2_ACCOUNT_ID,
  [string]$AccessKeyId = $env:R2_ACCESS_KEY_ID,
  [string]$SecretAccessKey = $env:R2_SECRET_ACCESS_KEY
)

$ErrorActionPreference = "Stop"

if (-not $MinimumRequiredVersion) {
  $MinimumRequiredVersion = $Version
}

if (-not $Bucket) { throw "Missing R2_BUCKET config or env var" }
if (-not $AccountId) { throw "Missing R2_ACCOUNT_ID config or env var" }
if (-not $AccessKeyId) { throw "Missing R2_ACCESS_KEY_ID config or env var" }
if (-not $SecretAccessKey) { throw "Missing R2_SECRET_ACCESS_KEY config or env var" }

$latestPath = Join-Path ([System.IO.Path]::GetTempPath()) "latest-rollback.json"
$payloadObj = @{
  version = $Version
  minimum_required_version = $MinimumRequiredVersion
  download_url = $DownloadUrl
  sha256 = $Sha256.ToLowerInvariant()
  published_at = (Get-Date).ToString("o")
}

if ($AppSha256) {
  $payloadObj["app_sha256"] = $AppSha256.ToLowerInvariant()
} else {
  $payloadObj["app_sha256"] = ""
}

$payload = $payloadObj | ConvertTo-Json -Depth 3

# Write UTF-8 without BOM to avoid JSON parser issues in clients.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($latestPath, $payload, $utf8NoBom)

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
  throw "aws CLI not found. Install it and retry."
}

$endpoint = "https://$AccountId.r2.cloudflarestorage.com"
$env:AWS_ACCESS_KEY_ID = $AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $SecretAccessKey
$env:AWS_DEFAULT_REGION = "auto"

aws s3 cp $latestPath "s3://$Bucket/latest.json" --endpoint-url $endpoint --cache-control "no-cache"
if ($LASTEXITCODE -ne 0) { throw "Failed to upload rollback latest.json to R2" }

Remove-Item -Force $latestPath -ErrorAction SilentlyContinue

Write-Output "=========================================================="
Write-Output "Rollback metadata successfully pinned on R2!"
Write-Output "Version: $Version"
Write-Output "Minimum Required: $MinimumRequiredVersion"
Write-Output "URL: $DownloadUrl"
Write-Output "SHA256: $Sha256"
Write-Output "=========================================================="
