@echo off
echo Starting Msafiri API Server...
cd /d "D:\development\msafiri-visitor-api"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the server
echo Starting uvicorn server...
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause