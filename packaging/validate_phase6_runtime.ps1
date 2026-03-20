param(
  [string]$BackendUrl = "http://127.0.0.1:58432",
  [string]$UpdateInfoUrl = "",
  [int]$TimeoutSec = 8,
  [int]$MaxAttempts = 8
)

$ErrorActionPreference = "Stop"

function Invoke-JsonGet {
  param(
    [string]$Url,
    [int]$Timeout = 8
  )
  $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $Timeout
  if ($resp.StatusCode -lt 200 -or $resp.StatusCode -ge 300) {
    throw "GET $Url failed with HTTP $($resp.StatusCode)"
  }
  if (-not $resp.Content) { return @{} }
  return ($resp.Content | ConvertFrom-Json)
}

function Wait-Until {
  param(
    [scriptblock]$Condition,
    [string]$Label,
    [int]$Attempts = 6,
    [int]$SleepSeconds = 2
  )
  for ($i = 1; $i -le $Attempts; $i++) {
    try {
      if (& $Condition) { return $true }
    } catch {
      # keep retrying
    }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for: $Label"
}

if (-not $UpdateInfoUrl) {
  try {
    $src = Get-Content "desktop/downloader_app.py" -Raw
    $m = [regex]::Match($src, "STREAMORE_UPDATE_BASE_URL',\s*'([^']+)'")
    if ($m.Success -and $m.Groups[1].Value) {
      $UpdateInfoUrl = ("{0}/latest.json" -f $m.Groups[1].Value.TrimEnd('/'))
    } else {
      $UpdateInfoUrl = "https://pub-de03d3c6527b425fa2ee53203c4ea5fc.r2.dev/latest.json"
    }
  } catch {
    $UpdateInfoUrl = "https://pub-de03d3c6527b425fa2ee53203c4ea5fc.r2.dev/latest.json"
  }
}

Write-Host "Phase 6 runtime validation..." -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl"
if ($UpdateInfoUrl) { Write-Host "Update URL: $UpdateInfoUrl" }

# 1) Backend health
Wait-Until -Label "backend health endpoint" -Attempts $MaxAttempts -Condition {
  $r = Invoke-WebRequest -UseBasicParsing -Uri "$BackendUrl/api/health" -TimeoutSec $TimeoutSec
  return ($r.StatusCode -eq 200)
} | Out-Null
Write-Host "  [OK] backend health is online" -ForegroundColor Green

# 2) aria2 status running
Wait-Until -Label "aria2 running status" -Attempts $MaxAttempts -Condition {
  $j = Invoke-JsonGet -Url "$BackendUrl/api/aria2/status" -Timeout $TimeoutSec
  $status = [string]($j.status)
  return ($status -eq "running")
} | Out-Null
$aria = Invoke-JsonGet -Url "$BackendUrl/api/aria2/status" -Timeout $TimeoutSec
Write-Host "  [OK] aria2 status: $($aria.status)" -ForegroundColor Green

# 3) downloads endpoint responsiveness
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$dl = Invoke-JsonGet -Url "$BackendUrl/api/downloads" -Timeout ([Math]::Max($TimeoutSec, 10))
$sw.Stop()
$count = 0
try { $count = @($dl.downloads).Count } catch { $count = 0 }
Write-Host "  [OK] /api/downloads responded in $([Math]::Round($sw.Elapsed.TotalSeconds,2))s ($count items)" -ForegroundColor Green

# 4) engine reset + recovery
Write-Host "  [..] testing engine reset and recovery..."
$resetResp = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BackendUrl/api/engine/reset" -TimeoutSec 25
if ($resetResp.StatusCode -lt 200 -or $resetResp.StatusCode -ge 300) {
  throw "Engine reset failed with HTTP $($resetResp.StatusCode)"
}
Wait-Until -Label "aria2 recovery after reset" -Attempts $MaxAttempts -SleepSeconds 3 -Condition {
  $j = Invoke-JsonGet -Url "$BackendUrl/api/aria2/status" -Timeout $TimeoutSec
  return ([string]$j.status -eq "running")
} | Out-Null
Write-Host "  [OK] engine reset recovered aria2" -ForegroundColor Green

# 5) update metadata contract
if ($UpdateInfoUrl) {
  $upd = Invoke-JsonGet -Url $UpdateInfoUrl -Timeout $TimeoutSec
  foreach ($k in @("version", "minimum_required_version", "download_url", "sha256")) {
    if (-not ($upd.PSObject.Properties.Name -contains $k)) {
      throw "latest.json missing required field: $k"
    }
  }
  Write-Host "  [OK] update metadata contract valid (version=$($upd.version), minimum=$($upd.minimum_required_version))" -ForegroundColor Green
}

Write-Host ""
Write-Host "Phase 6 runtime validation PASSED." -ForegroundColor Green
