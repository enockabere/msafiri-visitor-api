#!/usr/bin/env python3
"""Safe database reset - drops tables only, not schema"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, MetaData
from app.core.config import settings

def safe_reset():
    """Safely reset database by dropping tables only"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    print("🗑️  Dropping all tables...")
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'alembic_version'
        """))
        tables = [row[0] for row in result]
        
        # Drop each table
        for table in tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                print(f"  ✓ Dropped {table}")
            except Exception as e:
                print(f"  ⚠️  Could not drop {table}: {e}")
        
        # Drop alembic version table
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        
        # Drop enum types
        result = conn.execute(text("""
            SELECT typname FROM pg_type 
            WHERE typtype = 'e' AND typnamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = 'public'
            )
        """))
        enums = [row[0] for row in result]
        
        for enum_name in enums:
            try:
                conn.execute(text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))
                print(f"  ✓ Dropped enum {enum_name}")
            except Exception as e:
                print(f"  ⚠️  Could not drop enum {enum_name}: {e}")
        
        conn.commit()
    
    print("✅ Tables dropped")
    
    # Clear migration files
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        print("🗑️  Clearing migration files...")
        for file in versions_dir.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
                print(f"  ✓ Removed {file.name}")
    
    # Create fresh migration
    print("📝 Creating fresh migration...")
    exit_code = os.system("alembic revision --autogenerate -m 'initial_migration'")
    if exit_code != 0:
        print("❌ Failed to create migration")
        return False
    
    # Apply migration
    print("🚀 Applying migration...")
    exit_code = os.system("alembic upgrade head")
    if exit_code != 0:
        print("❌ Failed to apply migration")
        return False
    
    print("✅ Database reset complete!")
    return True

if __name__ == "__main__":
    safe_reset()