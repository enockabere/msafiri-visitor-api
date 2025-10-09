#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_accommodation_allocations_table():
    """Create accommodation_allocations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS accommodation_allocations (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER NOT NULL,
        accommodation_type VARCHAR(20) NOT NULL,
        room_id INTEGER REFERENCES rooms(id),
        vendor_accommodation_id INTEGER REFERENCES vendor_accommodations(id),
        guest_name VARCHAR(200) NOT NULL,
        guest_email VARCHAR(100),
        guest_phone VARCHAR(20),
        check_in_date DATE NOT NULL,
        check_out_date DATE NOT NULL,
        number_of_guests INTEGER NOT NULL,
        purpose VARCHAR(500),
        notes TEXT,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        created_by INTEGER
    );
    
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_tenant_id ON accommodation_allocations(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_room_id ON accommodation_allocations(room_id);
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_vendor_id ON accommodation_allocations(vendor_accommodation_id);
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_status ON accommodation_allocations(status);
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(create_table_sql))
            connection.commit()
            print("Successfully created accommodation_allocations table")
            
    except Exception as e:
        print(f"Error creating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating accommodation_allocations table...")
    success = create_accommodation_allocations_table()
    
    if success:
        print("Table creation completed successfully!")
    else:
        print("Table creation failed!")
        sys.exit(1)