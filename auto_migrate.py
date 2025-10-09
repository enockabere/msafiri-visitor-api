#!/usr/bin/env python3
"""
Auto Migration Script - Nuclear Reset Option
Completely resets migrations and creates fresh ones
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def nuclear_reset():
    """Nuclear option: delete all migrations and start fresh"""
    print("💥 NUCLEAR RESET: Deleting all migration files...")
    
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        for file in versions_dir.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
                print(f"🗑️ Deleted {file.name}")
    
    # Clear alembic version table
    print("🔄 Clearing migration history...")
    run_command("python -c \"from app.db.database import engine; engine.execute('DROP TABLE IF EXISTS alembic_version')\"", "Dropping alembic_version table")
    
    return True

def main():
    """Main migration function"""
    print("🚀 Starting MSafiri API Auto Migration (Nuclear Reset)")
    
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Please run from project root.")
        sys.exit(1)
    
    # Nuclear reset
    nuclear_reset()
    
    # Create fresh initial migration
    print("🔄 Creating fresh initial migration...")
    if run_command("alembic revision --autogenerate -m 'initial_migration'", "Creating initial migration"):
        if run_command("alembic upgrade head", "Running fresh migration"):
            print("🎉 Fresh migration completed successfully!")
            return
    
    # If that fails, try manual approach
    print("🔄 Trying manual database sync...")
    if run_command("alembic stamp head", "Stamping as current"):
        print("🎉 Database marked as up-to-date!")
        return
    
    print("❌ All migration attempts failed.")
    print("💡 Manual steps:")
    print("1. Check database connection")
    print("2. Ensure all tables exist")
    print("3. Run: alembic stamp head")
    sys.exit(1)

if __name__ == "__main__":
    main()