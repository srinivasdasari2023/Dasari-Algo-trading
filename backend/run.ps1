# Run CapitalGuard backend from the backend folder.
# Usage: from project root run:  .\backend\run.ps1
# Or:    cd backend then:        .\run.ps1

Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
Write-Host "Starting API from: $(Get-Location)"
Write-Host "Backend .env is loaded from project root or backend folder."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
