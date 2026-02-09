# Run MediScope Application
# Windows PowerShell script

Write-Host "Starting MediScope AI Agent..." -ForegroundColor Green

# Change to backend directory
Set-Location -Path "backend"

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Please run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-Not (Test-Path "..\\.env")) {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it." -ForegroundColor Yellow
    exit 1
}

# Run uvicorn
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press CTRL+C to stop" -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
