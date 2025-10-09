#!/usr/bin/env python3
"""
Safe Migration Script
Prevents common migration issues
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

def run_command(command, description):
    """Run command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False, None

def check_git_status():
    """Ensure git is clean before migration"""
    success, output = run_command("git status --porcelain", "Checking git status")
    if success and output.strip():
        print("⚠️ Warning: Uncommitted changes detected")
        print("💡 Commit changes before creating migrations")
        return False
    return True

def backup_database():
    """Create database backup before migration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ No DATABASE_URL found, skipping backup")
        return True
    
    success, _ = run_command(f"pg_dump {db_url} > {backup_file}", f"Creating backup: {backup_file}")
    return success

def main():
    """Safe migration workflow"""
    print("🛡️ Safe Migration Script")
    
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Run from project root.")
        sys.exit(1)
    
    # Check git status
    if not check_git_status():
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Pull latest changes
    run_command("git pull origin main", "Pulling latest changes")
    
    # Update to latest migrations
    success, _ = run_command("alembic upgrade head", "Updating to latest migrations")
    if not success:
        print("❌ Failed to update migrations. Fix issues before proceeding.")
        sys.exit(1)
    
    # Create backup (production only)
    if os.getenv("NODE_ENV") == "production":
        if not backup_database():
            response = input("Backup failed. Continue? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    # Create new migration
    message = input("Enter migration message: ").strip()
    if not message:
        print("❌ Migration message required")
        sys.exit(1)
    
    success, _ = run_command(f'alembic revision --autogenerate -m "{message}"', f"Creating migration: {message}")
    if not success:
        sys.exit(1)
    
    # Apply migration
    success, _ = run_command("alembic upgrade head", "Applying new migration")
    if not success:
        print("❌ Migration failed. Check the error above.")
        sys.exit(1)
    
    print("🎉 Migration completed successfully!")
    print("💡 Don't forget to commit the migration file:")
    print("   git add alembic/versions/")
    print(f'   git commit -m "Add migration: {message}"')

if __name__ == "__main__":
    main()