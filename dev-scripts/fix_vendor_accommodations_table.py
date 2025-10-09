#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_vendor_accommodations_table():
    """Add missing columns to vendor_accommodations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to add missing columns
    alter_table_sql = """
    -- Add missing columns to vendor_accommodations table
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS accommodation_type VARCHAR(100) NOT NULL DEFAULT 'Hotel';
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(20);
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS contact_email VARCHAR(100);
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS capacity INTEGER NOT NULL DEFAULT 1;
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS description TEXT;
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS current_occupants INTEGER NOT NULL DEFAULT 0;
    
    ALTER TABLE vendor_accommodations 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(alter_table_sql))
            connection.commit()
            print("Successfully added missing columns to vendor_accommodations table")
            
    except Exception as e:
        print(f"Error updating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Fixing vendor_accommodations table...")
    success = fix_vendor_accommodations_table()
    
    if success:
        print("Table fix completed successfully!")
    else:
        print("Table fix failed!")
        sys.exit(1)