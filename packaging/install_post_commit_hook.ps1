Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hookDir = Join-Path $repoRoot ".git\hooks"
$hookPath = Join-Path $hookDir "post-commit"

if (-not (Test-Path $hookDir)) {
  throw "Git hooks directory not found: $hookDir"
}

$hookScript = @"
#!/bin/sh
REPO_ROOT="`$(git rev-parse --show-toplevel)"
powershell -NoProfile -ExecutionPolicy Bypass -File "`$REPO_ROOT/packaging/post_commit_publish.ps1"
exit 0
"@

[System.IO.File]::WriteAllText($hookPath, $hookScript, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "Installed hook: $hookPath"
Write-Output "Auto-publish log: $env:TEMP\\streamore-auto-release.log"
