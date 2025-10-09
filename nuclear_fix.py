#!/usr/bin/env python3
"""
Nuclear Alembic Fix - Direct Database Cleanup
"""

import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    """Nuclear fix - clear database table directly"""
    print("💥 Nuclear Alembic Fix")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Drop alembic_version table completely
        print("1. Dropping alembic_version table...")
        cursor.execute("DROP TABLE IF EXISTS alembic_version;")
        conn.commit()
        print("✅ Dropped alembic_version table")
        
        cursor.close()
        conn.close()
        
        # Remove migration files
        print("2. Removing migration files...")
        versions_dir = Path("alembic/versions")
        if versions_dir.exists():
            for file in versions_dir.glob("*.py"):
                if file.name != "__init__.py":
                    file.unlink()
                    print(f"🗑️ Removed {file.name}")
        
        # Create base migration
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
    pass

def downgrade():
    pass
'''
        base_migration.write_text(base_content)
        print("✅ Created base migration")
        
        print("🎉 Nuclear fix complete!")
        print("💡 Now run: alembic stamp 001_base")
        
        return True
        
    except Exception as e:
        print(f"❌ Nuclear fix failed: {e}")
        return False

if __name__ == "__main__":
    main()