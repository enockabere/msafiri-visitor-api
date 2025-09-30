#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def check_vendor_accommodations_schema():
    """Check the current schema of vendor_accommodations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to check table schema
    check_schema_sql = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'vendor_accommodations'
    ORDER BY ordinal_position;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(check_schema_sql))
            columns = result.fetchall()
            
            print("Current vendor_accommodations table schema:")
            print("-" * 60)
            for column in columns:
                print(f"{column[0]:<25} {column[1]:<20} {column[2]:<10} {column[3] or 'None'}")
            
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_vendor_accommodations_schema()