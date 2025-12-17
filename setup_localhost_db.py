#!/usr/bin/env python3
"""
Script to set up localhost database with all required tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.database import Base
from app.models import *  # Import all models

def setup_database():
    """Set up the database with all tables"""
    
    print("Setting up localhost database...")
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Drop all tables
        print("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        
        print("Database setup completed successfully!")
        
        # Show created tables
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"\nCreated {len(tables)} tables:")
            for table in tables:
                print(f"  - {table}")
                
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False
        
    return True

def create_super_admin():
    """Create a super admin user"""
    try:
        from app.services.user_service import create_super_admin_user
        
        print("\nCreating super admin user...")
        
        # Create super admin with default credentials
        admin_data = {
            'email': 'admin@msf.org',
            'full_name': 'Super Admin',
            'password': 'admin123',  # Change this in production
            'role': 'super_admin'
        }
        
        result = create_super_admin_user(admin_data)
        if result:
            print("Super admin created successfully!")
            print("Email: admin@msf.org")
            print("Password: admin123")
            print("Please change the password after first login.")
        else:
            print("Failed to create super admin user")
            
    except Exception as e:
        print(f"Error creating super admin: {e}")

if __name__ == "__main__":
    print("MSafiri Localhost Database Setup")
    print("=" * 40)
    
    success = setup_database()
    
    if success:
        create_super_admin()
        print("\n" + "=" * 40)
        print("Setup completed! You can now start the API server.")
        print("Run: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\nSetup failed!")
        sys.exit(1)