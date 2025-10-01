#!/usr/bin/env python3
"""
Database Reset Script
This script will:
1. Drop all tables
2. Clear migration history
3. Create fresh initial migration
4. Apply migrations
"""

import os
import sys
import shutil
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models import *  # Import all models

def reset_database():
    """Reset database and migrations"""
    
    # 1. Connect to database
    engine = create_engine(settings.DATABASE_URL)
    
    print("🗑️  Dropping all tables...")
    with engine.connect() as conn:
        # Drop all tables
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    
    print("✅ All tables dropped")
    
    # 2. Clear migration versions directory
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        print("🗑️  Clearing migration files...")
        for file in versions_dir.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
        print("✅ Migration files cleared")
    
    # 3. Create fresh initial migration
    print("📝 Creating fresh initial migration...")
    exit_code = os.system("alembic revision --autogenerate -m 'initial_migration'")
    if exit_code != 0:
        print("❌ Failed to create migration")
        sys.exit(1)
    
    # 4. Apply migration
    print("🚀 Applying migration...")
    exit_code = os.system("alembic upgrade head")
    if exit_code != 0:
        print("❌ Failed to apply migration")
        sys.exit(1)
    
    print("✅ Database reset complete!")

if __name__ == "__main__":
    reset_database()