#!/usr/bin/env python3
"""
Auto Migration Script - Bypass Broken Migrations
Just ensures the server can start
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        return False

def main():
    """Main function - bypass migrations and ensure server starts"""
    print("🚀 MSafiri API - Bypassing Broken Migrations")
    
    if not Path("alembic.ini").exists():
        print("❌ alembic.ini not found. Please run from project root.")
        sys.exit(1)
    
    # Create empty __init__.py in versions if missing
    versions_init = Path("alembic/versions/__init__.py")
    if not versions_init.exists():
        versions_init.touch()
        print("✅ Created versions/__init__.py")
    
    # Try to create a simple base migration
    print("🔄 Creating minimal base migration...")
    base_migration = Path("alembic/versions/001_base.py")
    if not base_migration.exists():
        base_content = '''"""base migration

Revision ID: 001_base
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_base'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
'''
        base_migration.write_text(base_content)
        print("✅ Created base migration")
    
    # Try to stamp the database
    if run_command("alembic stamp 001_base", "Stamping database with base"):
        print("🎉 Database stamped successfully!")
        print("💡 Server should now start normally")
        print("🚀 Run: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    print("⚠️ Migration stamping failed, but server may still work")
    print("💡 Try starting the server anyway:")
    print("🚀 uvicorn app.main:app --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()