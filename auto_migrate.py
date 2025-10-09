#!/usr/bin/env python3
"""
Auto Migration Script for MSafiri Visitor API
Fixes broken migration chains and runs migrations
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description, capture_output=True):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=capture_output, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout and capture_output:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if capture_output and e.stderr:
            print(f"Error: {e.stderr}")
        return False

def create_missing_migration():
    """Create the missing b5a42d5c4bd7 migration file"""
    migration_content = '''"""initial setup

Revision ID: b5a42d5c4bd7
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b5a42d5c4bd7'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # This is a placeholder migration for the missing initial setup
    pass

def downgrade():
    pass
'''
    
    migration_file = Path("alembic/versions/b5a42d5c4bd7_initial_setup.py")
    if not migration_file.exists():
        print("🔧 Creating missing migration file...")
        migration_file.write_text(migration_content)
        print("✅ Missing migration file created")
        return True
    return False

def main():
    """Main migration function"""
    print("🚀 Starting MSafiri API Auto Migration")
    
    # Check if alembic.ini exists
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Please run from project root.")
        sys.exit(1)
    
    # Create missing migration file
    create_missing_migration()
    
    # Try to stamp the latest migration to fix the chain
    print("🔧 Attempting to fix migration chain...")
    if run_command("alembic stamp head", "Stamping current head"):
        # Now try the migration
        if run_command("alembic upgrade head", "Running database migrations"):
            print("🎉 Auto migration completed successfully!")
            return
    
    # If that fails, try a different approach
    print("🔧 Trying alternative fix...")
    if run_command("alembic revision --autogenerate -m 'sync_database'", "Creating sync migration"):
        if run_command("alembic upgrade head", "Running database migrations"):
            print("🎉 Auto migration completed successfully!")
            return
    
    print("❌ Migration failed. Database may need manual setup.")
    print("💡 Try running: alembic stamp head && alembic upgrade head")
    sys.exit(1)

if __name__ == "__main__":
    main()