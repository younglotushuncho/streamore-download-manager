param(
  [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$lockPath = Join-Path $env:TEMP "streamore-auto-release.lock"
$logPath = Join-Path $env:TEMP "streamore-auto-release.log"

try {
  # Skip if another auto-release appears to be active.
  if (Test-Path $lockPath) {
    $ageSec = ((Get-Date) - (Get-Item $lockPath).LastWriteTime).TotalSeconds
    if ($ageSec -lt (8 * 3600)) {
      exit 0
    }
    Remove-Item -Force $lockPath -ErrorAction SilentlyContinue
  }

  Set-Content -Path $lockPath -Value ("started=" + (Get-Date).ToString("o")) -Encoding ascii

  Push-Location $RepoRoot
  "=== Auto release started: $(Get-Date -Format o) ===" | Out-File -FilePath $logPath -Encoding utf8 -Append
  & powershell -NoProfile -ExecutionPolicy Bypass -File ".\packaging\build_nuitka.ps1" *>> $logPath
  "=== Auto release finished: $(Get-Date -Format o) ===" | Out-File -FilePath $logPath -Encoding utf8 -Append
} catch {
  $_ | Out-File -FilePath $logPath -Encoding utf8 -Append
} finally {
  Pop-Location -ErrorAction SilentlyContinue
  Remove-Item -Force $lockPath -ErrorAction SilentlyContinue
}

