#!/usr/bin/env python3
"""
Auto Migration Script - Production Ready
Uses fixed migration system
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        return False

def main():
    """Production migration workflow"""
    print("🚀 MSafiri API Auto Migration")
    
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Run from project root.")
        sys.exit(1)
    
    # Check if base migration exists
    base_migration = Path("alembic/versions/001_base_migration.py")
    if not base_migration.exists():
        print("⚠️ Base migration missing. Run fix_alembic.py first.")
        sys.exit(1)
    
    # Run migrations
    if run_command("alembic upgrade head", "Running database migrations"):
        print("🎉 Migration completed successfully!")
        print("🚀 Server ready to start")
        return
    
    print("❌ Migration failed. Run fix_alembic.py to reset.")
    sys.exit(1)

if __name__ == "__main__":
    main()