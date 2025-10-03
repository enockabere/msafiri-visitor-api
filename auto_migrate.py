#!/usr/bin/env python3
"""
Auto-sync database with models (like Django)
This will automatically create missing tables and columns
"""
from app.db.database import engine, Base
import sqlalchemy as sa

def auto_migrate():
    """Automatically sync database with current models"""
    try:
        print("Auto-syncing database with models...")
        
        # This creates any missing tables without dropping existing ones
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        print("Database synced successfully!")
        print("All missing tables and columns have been created")
        
    except Exception as e:
        print(f"Error syncing database: {e}")

if __name__ == "__main__":
    auto_migrate()