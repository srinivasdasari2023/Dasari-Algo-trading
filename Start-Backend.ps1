# Start CapitalGuard API from project root. Uses backend's venv and PYTHONPATH
# so the correct app (backend/app) loads even when run from root.
# Usage: .\Start-Backend.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating backend virtual environment..."
    Set-Location $BackendDir
    python -m venv .venv
    Set-Location $ProjectRoot
}

$env:PYTHONPATH = $BackendDir
Write-Host "Starting CapitalGuard API (app from backend folder)..."
Write-Host "Backend: $BackendDir"
Write-Host "Web app: http://localhost:3000 (run 'cd web; npm run dev' in another terminal if needed)"
# Open browser to the app after a short delay (frontend must be running separately)
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://localhost:3000" } | Out-Null
& $VenvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
