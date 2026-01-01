#!/usr/bin/env python3
"""
Script to delete all badge templates and related records
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create database connection
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def delete_all_badge_templates():
    db = SessionLocal()
    try:
        print("Deleting all badge templates and related records...")
        
        # Delete in correct order to avoid foreign key constraints
        db.execute(text("DELETE FROM participant_badges"))
        print("✓ Deleted all participant badges")
        
        db.execute(text("DELETE FROM event_badges"))
        print("✓ Deleted all event badges")
        
        db.execute(text("DELETE FROM badge_templates"))
        print("✓ Deleted all badge templates")
        
        db.commit()
        print("✅ All badge templates deleted successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_badge_templates()