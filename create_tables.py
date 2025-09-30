#!/usr/bin/env python3
"""
Create database tables directly using SQLAlchemy
"""
import sys
import os
sys.path.append('.')

from app.db.database import Base, engine
from app.models import *  # Import all models

def create_tables():
    """Create all database tables"""
    try:
        print("Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("Tables created successfully!")
        return True
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)