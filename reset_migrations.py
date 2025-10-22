#!/usr/bin/env python3
"""
Reset Alembic migrations and create fresh initial migration
"""
import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.database import Base
from app.models import *  # Import all models

def reset_migrations():
    """Reset migrations and create fresh initial migration"""
    
    print("Starting migration reset...")
    
    # 1. Remove all migration files
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        print("Removing existing migration files...")
        shutil.rmtree(versions_dir)
        versions_dir.mkdir()
        print("Migration files removed")
    
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
    
    # 3. Create fresh initial migration
    print("Creating fresh initial migration...")
    os.system("alembic revision --autogenerate -m 'Initial migration'")
    
    # 4. Apply the migration
    print("Applying initial migration...")
    os.system("alembic upgrade head")
    
    print("Migration reset complete!")

if __name__ == "__main__":
    reset_migrations()