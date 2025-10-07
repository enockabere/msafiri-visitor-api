#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_fcm_token_column():
    """Add FCM token column to users table"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                print("🔄 Adding FCM token column to users table...")
                
                # Add FCM token column
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(500)
                """))
                
                print("✅ FCM token column added successfully")
                
                # Commit transaction
                trans.commit()
                print("🎉 Migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {str(e)}")
                raise
                
    except SQLAlchemyError as e:
        print(f"❌ Database connection error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    add_fcm_token_column()