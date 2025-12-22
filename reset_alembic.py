#!/usr/bin/env python3
"""
Reset alembic to clean state and set baseline
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_database_url():
    return os.getenv('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/msafiri_db')

def reset_alembic():
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Resetting alembic to clean state...")
        
        # Clear alembic version table
        db.execute(text("DELETE FROM alembic_version"))
        
        # Set to our new baseline
        db.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_initial_schema')"))
        
        db.commit()
        print("Alembic reset to baseline: 001_initial_schema")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reset_alembic()