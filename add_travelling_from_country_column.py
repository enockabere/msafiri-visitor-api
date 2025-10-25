#!/usr/bin/env python3
"""
Add travelling_from_country column to public_registrations table
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def add_travelling_from_country_column():
    """Add travelling_from_country column to public_registrations table"""
    
    # Database connection
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/msafiri_db")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            check_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'public_registrations' 
                AND column_name = 'travelling_from_country'
            """)
            
            result = conn.execute(check_column).fetchone()
            
            if result:
                print("Column 'travelling_from_country' already exists in public_registrations table")
                return True
            
            # Add the column
            add_column_sql = text("""
                ALTER TABLE public_registrations 
                ADD COLUMN travelling_from_country VARCHAR(100)
            """)
            
            conn.execute(add_column_sql)
            conn.commit()
            
            print("Successfully added 'travelling_from_country' column to public_registrations table")
            return True
            
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = add_travelling_from_country_column()
    sys.exit(0 if success else 1)