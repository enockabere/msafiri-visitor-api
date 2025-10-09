#!/usr/bin/env python3
"""
Reset database migration state
"""
import os
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_migration_state():
    """Reset the alembic_version table"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Drop alembic_version table
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
            print("Dropped alembic_version table")
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if reset_migration_state():
        print("Migration state reset successfully")
        print("Now run: alembic revision --autogenerate -m 'initial'")
        print("Then run: alembic upgrade head")
    else:
        print("Failed to reset migration state")
        sys.exit(1)