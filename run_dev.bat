@echo off
echo Starting Msafiri Visitor System API...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000