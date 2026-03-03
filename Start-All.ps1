# Start both Backend (port 8000) and Web app (port 3000), then open the dashboard.
# Run from project root: .\Start-All.ps1
# Keep both terminal windows open. Close them to stop the servers.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$WebDir = Join-Path $ProjectRoot "web"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating backend virtual environment..."
    Set-Location $BackendDir
    python -m venv .venv
    Set-Location $ProjectRoot
}

Write-Host "Starting Backend (new window)..."
$backendCmd = "Set-Location '$BackendDir'; `$env:PYTHONPATH='$BackendDir'; & '$VenvPython' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "Waiting 5s for backend to start..."
Start-Sleep -Seconds 5

Write-Host "Starting Web app (new window)..."
$webCmd = "Set-Location '$WebDir'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $webCmd

Write-Host "Waiting 10s for Next.js to start..."
Start-Sleep -Seconds 10

Write-Host "Opening http://localhost:3000 in browser..."
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Done. Two terminal windows are running:"
Write-Host "  - Backend: http://127.0.0.1:8000 (do not close that window)"
Write-Host "  - Web app: http://localhost:3000 (do not close that window)"
Write-Host "Close this window when you like. To stop servers, close the other two windows."
