#!/usr/bin/env python3
"""
Fix production migrations by stamping current state
"""
import os
from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_production_migrations():
    """Fix production migrations by stamping current state"""
    
    print("Starting production migration fix...")
    
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
    
    # Stamp current state as initial migration
    print("Stamping current database state as initial migration...")
    os.system("python -m alembic stamp head")
    
    print("Production migration fix complete!")
    print("You can now run 'python -m alembic upgrade head' for future migrations")

if __name__ == "__main__":
    fix_production_migrations()