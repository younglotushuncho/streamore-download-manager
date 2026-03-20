# Start YTS Movie Monitor - Complete Setup
# This script starts aria2 daemon and Flask backend

Write-Host "Starting YTS Movie Monitor..." -ForegroundColor Cyan
Write-Host ""

# Stop any existing processes
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow
Stop-Process -Name aria2c,python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Start aria2c daemon
Write-Host "Starting aria2c daemon..." -ForegroundColor Green
$aria2Process = Start-Process -FilePath ".\bin\aria2c.exe" `
    -ArgumentList '--enable-rpc','--rpc-listen-all=false','--rpc-allow-origin-all','--rpc-listen-port=6800','--max-concurrent-downloads=5','--dir=E:\movie_downloads' `
    -WindowStyle Hidden -PassThru

if ($aria2Process) {
    Write-Host "  aria2c started (PID: $($aria2Process.Id))" -ForegroundColor Green
}
else {
    Write-Host "  Failed to start aria2c" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 1

# Start backend
# Start backend
Write-Host "Starting Flask backend..." -ForegroundColor Green
# Resolve python executable to use for starting backend
function Resolve-PythonExecutable {
    # Prefer LocalAppData installs (real python.exe) before App Execution Aliases
    $possible = @(
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:LocalAppData\Programs\Python\Python310\python.exe",
        "$env:LocalAppData\Programs\Python\Python39\python.exe",
        "C:\\Python312\\python.exe",
        "C:\\Python39\\python.exe",
        "C:\\Python38\\python.exe"
    )
    foreach ($p in $possible) {
        if (Test-Path $p) { return $p }
    }

    # Try 'python' on PATH (may be WindowsApps alias)
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # Try 'py' launcher
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in $possible) {
        if (Test-Path $p) { return $p }
    }

    return $null
}

$pythonExe = Resolve-PythonExecutable
Write-Host "  Using python executable: $pythonExe" -ForegroundColor Cyan
if (-not $pythonExe) {
    Write-Host "  Python executable not found. Install Python or add it to PATH, or provide the path to python.exe." -ForegroundColor Red
    Write-Host "  You can download from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is selected." -ForegroundColor Yellow
    exit 1
}

# Check if it's the WindowsApps stub (not a real Python installation)
if ($pythonExe -match 'WindowsApps') {
    Write-Host ""
    Write-Host "ERROR: Detected Microsoft Store Python stub instead of real Python installation." -ForegroundColor Red
    Write-Host ""
    Write-Host "The resolved python.exe at:" -ForegroundColor Yellow
    Write-Host "  $pythonExe" -ForegroundColor White
    Write-Host "is just a launcher stub that won't run the backend." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "SOLUTION - Choose one:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Option 1: Install Real Python (RECOMMENDED)" -ForegroundColor Green
    Write-Host "  1. Download from: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "  2. Run installer and CHECK 'Add Python to PATH'" -ForegroundColor White
    Write-Host "  3. Re-run this script" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2: Disable Windows Store Alias" -ForegroundColor Green
    Write-Host "  1. Open Settings -> Apps -> Advanced app execution aliases" -ForegroundColor White
    Write-Host "  2. Turn OFF 'python.exe' and 'python3.exe' aliases" -ForegroundColor White
    Write-Host "  3. Install Python from python.org" -ForegroundColor White
    Write-Host "  4. Re-run this script" -ForegroundColor White
    Write-Host ""
    exit 1
}

$backendProcess = Start-Process -FilePath $pythonExe `
    -ArgumentList '-u','-m','backend.app' `
    -WindowStyle Hidden -PassThru

if ($backendProcess) {
    Write-Host "  Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green
}
else {
    Write-Host "  Failed to start backend" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 3

# Test connectivity
Write-Host ""
Write-Host "Testing connectivity..." -ForegroundColor Yellow

# Wait for backend health (poll up to 30 seconds)
$maxWait = 30
$elapsed = 0
$health = $null
while ($elapsed -lt $maxWait) {
    try {
        $health = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/health -TimeoutSec 3 -ErrorAction Stop
        if ($health) {
            Write-Host "  Backend is healthy" -ForegroundColor Green
            break
        }
    }
    catch {
        # ignore, we'll retry
    }
    Start-Sleep -Seconds 1
    $elapsed += 1
}
if (-not $health) {
    Write-Host "  Backend health check failed after $maxWait seconds." -ForegroundColor Red
}

try {
    $aria2Status = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/aria2/status -TimeoutSec 5 -ErrorAction Stop
    if ($aria2Status.success) {
        Write-Host "  aria2 version $($aria2Status.version) is running" -ForegroundColor Green
    }
    else {
        Write-Host "  aria2 error: $($aria2Status.error)" -ForegroundColor Red
    }
}
catch {
    Write-Host "  aria2 status check failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "YTS Movie Monitor is ready!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend URL: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "Downloads Directory: E:\movie_downloads" -ForegroundColor White
Write-Host ""
Write-Host "To start the frontend GUI:" -ForegroundColor Yellow
Write-Host "  python -m frontend.main" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  Stop-Process -Name aria2c,python -Force" -ForegroundColor White
Write-Host ""
