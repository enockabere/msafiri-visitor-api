#!/usr/bin/env python3
"""
Reset database and create all tables from models
This bypasses Alembic migration issues
"""
from app.db.database import engine, Base
from app.models import *  # Import all models

def reset_database():
    """Drop all tables and recreate from models"""
    try:
        print("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("🏗️  Creating all tables from models...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database reset complete!")
        print("📝 Remember to run: alembic stamp head")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()