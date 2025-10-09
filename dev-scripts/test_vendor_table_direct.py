#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def test_vendor_accommodation_insert():
    """Test inserting data into vendor_accommodations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to insert test data
    insert_sql = """
    INSERT INTO vendor_accommodations 
    (tenant_id, vendor_name, accommodation_type, location, contact_person, contact_phone, contact_email, capacity, description, is_active, current_occupants) 
    VALUES 
    (2, 'Test Hotel Direct', 'Hotel', 'Naivasha', 'Test Person', '0877727287', 'test@example.com', 10, 'Test description', true, 0)
    RETURNING id, vendor_name, accommodation_type, created_at;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(insert_sql))
            row = result.fetchone()
            connection.commit()
            
            print(f"Successfully inserted vendor accommodation:")
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Type: {row[2]}")
            print(f"Created at: {row[3]}")
            
            return True
            
    except Exception as e:
        print(f"Error inserting data: {e}")
        return False

if __name__ == "__main__":
    print("Testing direct vendor accommodation insertion...")
    success = test_vendor_accommodation_insert()
    
    if success:
        print("Direct database test completed successfully!")
        print("The accommodation_type column issue has been resolved!")
    else:
        print("Direct database test failed!")
        sys.exit(1)