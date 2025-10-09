#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_created_by_column():
    """Make created_by column nullable in vendor_accommodations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to make created_by nullable
    alter_sql = """
    ALTER TABLE vendor_accommodations 
    ALTER COLUMN created_by DROP NOT NULL;
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(alter_sql))
            connection.commit()
            print("Successfully made created_by column nullable")
            
    except Exception as e:
        print(f"Error updating column: {e}")
        return False
    
    return True

def test_insert_with_created_by():
    """Test inserting data with created_by field"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to insert test data with created_by
    insert_sql = """
    INSERT INTO vendor_accommodations 
    (tenant_id, vendor_name, accommodation_type, location, contact_person, contact_phone, contact_email, capacity, description, is_active, current_occupants, created_by) 
    VALUES 
    (2, 'Test Hotel with Created By', 'Hotel', 'Naivasha', 'Test Person', '0877727287', 'test@example.com', 10, 'Test description', true, 0, 'system')
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
    print("Fixing created_by column constraint...")
    success1 = fix_created_by_column()
    
    if success1:
        print("Testing vendor accommodation insertion with created_by...")
        success2 = test_insert_with_created_by()
        
        if success2:
            print("All tests completed successfully!")
            print("The vendor_accommodations table is now properly configured!")
        else:
            print("Insert test failed!")
            sys.exit(1)
    else:
        print("Column fix failed!")
        sys.exit(1)