#!/usr/bin/env python3
"""
Simple migration generator script similar to Django's makemigrations
Usage: python makemigrations.py "migration_name"
"""
import sys
import subprocess
from datetime import datetime

def make_migration(name):
    """Generate a new migration file"""
    try:
        # Use alembic revision --autogenerate to create migration
        cmd = ["alembic", "revision", "--autogenerate", "-m", name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Migration created successfully: {name}")
            print(result.stdout)
        else:
            print(f"❌ Error creating migration: {name}")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")

def migrate():
    """Apply all pending migrations"""
    try:
        cmd = ["alembic", "upgrade", "head"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migrations applied successfully")
            print(result.stdout)
        else:
            print("❌ Error applying migrations")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python makemigrations.py 'migration_name'  # Create new migration")
        print("  python makemigrations.py migrate           # Apply migrations")
        sys.exit(1)
    
    if sys.argv[1] == "migrate":
        migrate()
    else:
        make_migration(sys.argv[1])