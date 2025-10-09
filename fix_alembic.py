#!/usr/bin/env python3
"""
Permanent Alembic Fix Script
Resolves migration chain issues once and for all
"""

import subprocess
import sys
import os
from pathlib import Path
import psycopg2
from urllib.parse import urlparse

def run_sql(query, description):
    """Execute SQL directly on database"""
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL not found")
            return False
            
        # Parse database URL
        parsed = urlparse(db_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],  # Remove leading /
            user=parsed.username,
            password=parsed.password
        )
        
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ {description}")
        return True
        
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def main():
    """Fix Alembic permanently"""
    print("🔧 Permanent Alembic Fix")
    
    # Step 1: Clear alembic version table
    print("1. Clearing migration history...")
    run_sql("DROP TABLE IF EXISTS alembic_version;", "Dropped alembic_version table")
    
    # Step 2: Remove all migration files
    print("2. Removing broken migration files...")
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        for file in versions_dir.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
                print(f"🗑️ Removed {file.name}")
    
    # Step 3: Create single base migration
    print("3. Creating base migration...")
    base_migration = versions_dir / "001_base_migration.py"
    base_content = '''"""Base migration

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
    # Database already exists, this is just a marker
    pass

def downgrade():
    pass
'''
    base_migration.write_text(base_content)
    print("✅ Created base migration")
    
    # Step 4: Stamp database with base
    print("4. Stamping database...")
    try:
        result = subprocess.run(
            ["alembic", "stamp", "001_base"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ Database stamped successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Stamping failed: {e}")
        return False
    
    # Step 5: Test upgrade
    print("5. Testing upgrade...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ Upgrade test successful")
    except subprocess.CalledProcessError as e:
        print(f"❌ Upgrade test failed: {e}")
        return False
    
    print("🎉 Alembic fixed permanently!")
    print("💡 Future migrations will work normally:")
    print("   alembic revision --autogenerate -m 'description'")
    print("   alembic upgrade head")
    
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)