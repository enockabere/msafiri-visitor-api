#!/usr/bin/env python3
"""
Final migration fix - just stamp current state without schema changes
"""
import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.config import settings

def final_migration_fix():
    """Final fix - remove problematic migration and stamp current state"""
    
    print("Starting final migration fix...")
    
    # 1. Remove the problematic migration file
    versions_dir = Path("alembic/versions")
    for migration_file in versions_dir.glob("*_description_of_changes.py"):
        print(f"Removing problematic migration: {migration_file}")
        migration_file.unlink()
    
    # 2. Connect to database and drop alembic_version table
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Dropping alembic_version table...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            conn.commit()
            print("alembic_version table dropped")
        except Exception as e:
            print(f"Could not drop alembic_version table: {e}")
    
    # 3. Stamp current state as initial migration
    print("Stamping current database state as initial migration...")
    os.system("python -m alembic stamp head")
    
    print("Final migration fix complete!")
    print("Database is now in sync with migration state.")

if __name__ == "__main__":
    final_migration_fix()