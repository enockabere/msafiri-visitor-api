#!/usr/bin/env python3
"""
Script to fix Alembic migration issues by running upgrade command
"""
import subprocess
import sys
import os

def run_alembic_upgrade():
    """Run alembic upgrade head command"""
    try:
        # Change to the project directory
        os.chdir('/home/leo-server/projects/msafiri/msafiri-visitor-api')
        
        # Activate virtual environment and run alembic
        result = subprocess.run([
            'bash', '-c', 
            'source venv/bin/activate && alembic upgrade head'
        ], capture_output=True, text=True)
        
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running alembic: {e}")
        return False

if __name__ == "__main__":
    success = run_alembic_upgrade()
    sys.exit(0 if success else 1)