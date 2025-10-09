#!/usr/bin/env python3
"""
Auto Migration Script for MSafiri Visitor API
This script handles automatic database migrations using Alembic
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting MSafiri API Auto Migration")
    
    # Check if alembic.ini exists
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Please run from project root.")
        sys.exit(1)
    
    # Run migrations
    if not run_command("alembic upgrade head", "Running database migrations"):
        print("❌ Migration failed. Please check the error above.")
        sys.exit(1)
    
    print("🎉 Auto migration completed successfully!")

if __name__ == "__main__":
    main()