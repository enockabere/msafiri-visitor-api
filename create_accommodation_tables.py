#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_accommodation_tables():
    """Create accommodation tables"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    create_tables_sql = """
    -- GuestHouses table
    CREATE TABLE IF NOT EXISTS guesthouses (
        id SERIAL PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        address TEXT NOT NULL,
        facilities TEXT,
        contact_person VARCHAR NOT NULL,
        total_rooms INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_by VARCHAR NOT NULL
    );
    
    -- Rooms table
    CREATE TABLE IF NOT EXISTS rooms (
        id SERIAL PRIMARY KEY,
        guesthouse_id INTEGER NOT NULL REFERENCES guesthouses(id) ON DELETE CASCADE,
        room_number VARCHAR NOT NULL,
        capacity INTEGER NOT NULL,
        type VARCHAR NOT NULL,
        gender_restriction VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Room Allocations table
    CREATE TABLE IF NOT EXISTS room_allocations (
        id SERIAL PRIMARY KEY,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        visitor_id INTEGER NOT NULL,
        check_in_date TIMESTAMP WITH TIME ZONE NOT NULL,
        check_out_date TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_by VARCHAR NOT NULL
    );
    
    -- Vendor Accommodations table
    CREATE TABLE IF NOT EXISTS vendor_accommodations (
        id SERIAL PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        vendor_name VARCHAR NOT NULL,
        location VARCHAR NOT NULL,
        contact_person VARCHAR NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_by VARCHAR NOT NULL
    );
    
    -- Vendor Allocations table
    CREATE TABLE IF NOT EXISTS vendor_allocations (
        id SERIAL PRIMARY KEY,
        vendor_accommodation_id INTEGER NOT NULL REFERENCES vendor_accommodations(id) ON DELETE CASCADE,
        visitor_id INTEGER NOT NULL,
        check_in_date TIMESTAMP WITH TIME ZONE NOT NULL,
        check_out_date TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_by VARCHAR NOT NULL
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_guesthouses_tenant_id ON guesthouses(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_rooms_guesthouse_id ON rooms(guesthouse_id);
    CREATE INDEX IF NOT EXISTS idx_room_allocations_room_id ON room_allocations(room_id);
    CREATE INDEX IF NOT EXISTS idx_room_allocations_visitor_id ON room_allocations(visitor_id);
    CREATE INDEX IF NOT EXISTS idx_vendor_accommodations_tenant_id ON vendor_accommodations(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_vendor_allocations_vendor_id ON vendor_allocations(vendor_accommodation_id);
    CREATE INDEX IF NOT EXISTS idx_vendor_allocations_visitor_id ON vendor_allocations(visitor_id);
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(create_tables_sql))
            connection.commit()
            print("Successfully created accommodation tables")
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating accommodation tables...")
    success = create_accommodation_tables()
    
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")
        sys.exit(1)