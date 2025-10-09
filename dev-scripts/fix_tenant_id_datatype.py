#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_tenant_id_datatype():
    """Fix tenant_id column datatype from VARCHAR to INTEGER"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to alter the tenant_id column type
    alter_sql = """
    -- First, update any non-numeric tenant_id values to numeric if needed
    -- Then alter the column type to INTEGER
    ALTER TABLE vendor_accommodations 
    ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER;
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(alter_sql))
            connection.commit()
            print("Successfully changed tenant_id column type to INTEGER")
            
    except Exception as e:
        print(f"Error updating column type: {e}")
        return False
    
    return True

def verify_fix():
    """Verify the fix by testing a query"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # Test query that was failing
    test_sql = """
    SELECT id, vendor_name, accommodation_type, tenant_id
    FROM vendor_accommodations 
    WHERE tenant_id = 2
    LIMIT 5;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(test_sql))
            rows = result.fetchall()
            
            print(f"Query test successful! Found {len(rows)} records:")
            for row in rows:
                print(f"  ID: {row[0]}, Name: {row[1]}, Type: {row[2]}, Tenant ID: {row[3]}")
            
            return True
            
    except Exception as e:
        print(f"Query test failed: {e}")
        return False

if __name__ == "__main__":
    print("Fixing tenant_id column datatype...")
    success1 = fix_tenant_id_datatype()
    
    if success1:
        print("Testing the fix...")
        success2 = verify_fix()
        
        if success2:
            print("Fix completed successfully! The GET endpoint should now work.")
        else:
            print("Fix verification failed!")
            sys.exit(1)
    else:
        print("Column type fix failed!")
        sys.exit(1)