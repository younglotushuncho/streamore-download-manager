Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($env:STREAMORE_SKIP_AUTO_PUBLISH -eq "1") {
  exit 0
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

try {
  $msg = (git -C $repoRoot log -1 --pretty=%B) -join "`n"
} catch {
  exit 0
}

if ($msg -match "\[skip-release\]") {
  exit 0
}

try {
  $changed = git -C $repoRoot diff-tree --no-commit-id --name-only -r HEAD
} catch {
  exit 0
}

if (-not $changed) {
  exit 0
}

$relevant = $changed | Where-Object { $_ -match '^(desktop|backend|shared|packaging|bin)/' }
if (-not $relevant) {
  exit 0
}

$runner = Join-Path $repoRoot "packaging\run_auto_release.ps1"
if (-not (Test-Path $runner)) {
  exit 0
}

Start-Process powershell `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $runner,
    "-RepoRoot", $repoRoot
  ) | Out-Null

exit 0

