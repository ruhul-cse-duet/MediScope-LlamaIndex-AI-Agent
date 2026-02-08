@echo off
REM Run MediScope Application
REM Windows Batch script

echo Starting MediScope AI Agent...
echo.

REM Change to backend directory
cd backend

REM Check if .env file exists
if not exist "..\.env" (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Run uvicorn
echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo Press CTRL+C to stop
echo.

echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo Press CTRL+C to stop
echo.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
