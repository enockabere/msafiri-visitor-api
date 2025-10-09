#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def cleanup_test_data():
    """Remove test data from vendor_accommodations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to remove test data
    cleanup_sql = """
    DELETE FROM vendor_accommodations 
    WHERE vendor_name LIKE 'Test Hotel%';
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(cleanup_sql))
            connection.commit()
            print(f"Cleaned up {result.rowcount} test records from vendor_accommodations table")
            
    except Exception as e:
        print(f"Error cleaning up data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Cleaning up test data...")
    success = cleanup_test_data()
    
    if success:
        print("Cleanup completed successfully!")
    else:
        print("Cleanup failed!")
        sys.exit(1)