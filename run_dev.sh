# File: run_dev.sh (Linux/Mac shell script)
#!/bin/bash
echo "Starting Msafiri Visitor System API..."
echo

# Activate virtual environment
source venv/bin/activate

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# File: setup_db.bat (Windows database setup)
@echo off
echo Setting up database...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Initialize Alembic (only run once)
echo Initializing Alembic...
alembic init alembic

REM Create first migration
echo Creating initial migration...
alembic revision --autogenerate -m "Initial migration"

REM Run migrations
echo Running migrations...
alembic upgrade head

echo Database setup complete!

# File: setup_db.sh (Linux/Mac database setup)
#!/bin/bash
echo "Setting up database..."
echo

# Activate virtual environment
source venv/bin/activate

# Initialize Alembic (only run once)
echo "Initializing Alembic..."
alembic init alembic

# Create first migration
echo "Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

# Run migrations
echo "Running migrations..."
alembic upgrade head

echo "Database setup complete!"