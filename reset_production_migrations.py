#!/usr/bin/env python3
"""
Reset production database migrations
"""
import os
from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_production_migrations():
    """Reset production migrations only (don't drop tables)"""
    
    print("Starting production migration reset...")
    
    # Connect to production database
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Dropping alembic_version table...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            conn.commit()
            print("alembic_version table dropped")
        except Exception as e:
            print(f"Could not drop alembic_version table: {e}")
    
    # Mark current state as initial migration
    print("Marking current database state as initial migration...")
    os.system("alembic stamp head")
    
    print("Production migration reset complete!")

if __name__ == "__main__":
    reset_production_migrations()