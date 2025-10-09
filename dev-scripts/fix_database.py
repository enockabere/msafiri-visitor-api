#!/usr/bin/env python3
"""
Drop and recreate database tables with correct schema
"""
import sys
import os
sys.path.append('.')

from app.db.database import Base, engine
from app.models import *  # Import all models

def fix_database():
    """Drop and recreate all database tables"""
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("Creating all tables with correct schema...")
        Base.metadata.create_all(bind=engine)
        
        print("Database schema fixed successfully!")
        return True
        
    except Exception as e:
        print(f"Error fixing database: {e}")
        return False

if __name__ == "__main__":
    success = fix_database()
    sys.exit(0 if success else 1)