#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_transport_tables():
    """Create transport booking tables"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to create transport booking tables
    create_tables_sql = """
    -- Create transport booking tables
    
    -- Transport vendors table
    CREATE TABLE IF NOT EXISTS transport_vendors (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        vendor_type VARCHAR(50) NOT NULL CHECK (vendor_type IN ('absolute_taxi', 'manual_vendor')),
        contact_person VARCHAR(255),
        phone VARCHAR(50),
        email VARCHAR(255),
        api_endpoint VARCHAR(500),
        api_key VARCHAR(255),
        api_config JSON,
        is_active BOOLEAN DEFAULT TRUE,
        created_by VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Transport bookings table
    CREATE TABLE IF NOT EXISTS transport_bookings (
        id SERIAL PRIMARY KEY,
        booking_type VARCHAR(50) NOT NULL CHECK (booking_type IN ('airport_pickup', 'event_transfer', 'office_visit', 'custom')),
        status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'package_collected', 'visitor_picked_up', 'in_transit', 'completed', 'cancelled')),
        participant_ids JSON NOT NULL,
        pickup_locations JSON NOT NULL,
        destination VARCHAR(500) NOT NULL,
        scheduled_time TIMESTAMP NOT NULL,
        
        -- Welcome package integration
        has_welcome_package BOOLEAN DEFAULT FALSE,
        package_pickup_location VARCHAR(500),
        package_collected BOOLEAN DEFAULT FALSE,
        package_collected_at TIMESTAMP,
        package_collected_by VARCHAR(255),
        
        -- Vendor details
        vendor_type VARCHAR(50) NOT NULL CHECK (vendor_type IN ('absolute_taxi', 'manual_vendor')),
        vendor_name VARCHAR(255),
        driver_name VARCHAR(255),
        driver_phone VARCHAR(50),
        driver_email VARCHAR(255),
        vehicle_details VARCHAR(255),
        
        -- API integration
        external_booking_id VARCHAR(255),
        api_response JSON,
        
        -- Instructions and notes
        special_instructions TEXT,
        admin_notes TEXT,
        
        -- Tracking
        visitor_picked_up BOOLEAN DEFAULT FALSE,
        visitor_picked_up_at TIMESTAMP,
        completed_at TIMESTAMP,
        
        -- Flight details (for airport pickups)
        flight_number VARCHAR(50),
        arrival_time TIMESTAMP,
        
        -- Event reference (for event transfers)
        event_id INTEGER REFERENCES events(id),
        
        -- Admin tracking
        created_by VARCHAR(255) NOT NULL,
        confirmed_by VARCHAR(255),
        confirmed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Transport status updates table
    CREATE TABLE IF NOT EXISTS transport_status_updates (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER NOT NULL REFERENCES transport_bookings(id) ON DELETE CASCADE,
        status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'confirmed', 'package_collected', 'visitor_picked_up', 'in_transit', 'completed', 'cancelled')),
        notes TEXT,
        location VARCHAR(255),
        updated_by VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_transport_bookings_status ON transport_bookings(status);
    CREATE INDEX IF NOT EXISTS idx_transport_bookings_type ON transport_bookings(booking_type);
    CREATE INDEX IF NOT EXISTS idx_transport_bookings_scheduled_time ON transport_bookings(scheduled_time);
    CREATE INDEX IF NOT EXISTS idx_transport_bookings_event_id ON transport_bookings(event_id);
    CREATE INDEX IF NOT EXISTS idx_transport_status_updates_booking_id ON transport_status_updates(booking_id);
    CREATE INDEX IF NOT EXISTS idx_transport_vendors_active ON transport_vendors(is_active);
    
    -- Insert default transport vendors
    INSERT INTO transport_vendors (name, vendor_type, contact_person, phone, email, is_active, created_by)
    VALUES 
        ('Absolute Taxi', 'absolute_taxi', 'Absolute Taxi Support', '+254700000000', 'support@absolutetaxi.com', TRUE, 'system'),
        ('Manual Taxi Service', 'manual_vendor', 'Admin', '+254700000001', 'admin@msf.org', TRUE, 'system')
    ON CONFLICT DO NOTHING;
    
    COMMIT;
    """
    
    try:
        with engine.connect() as connection:
            # Execute the SQL
            connection.execute(text(create_tables_sql))
            connection.commit()
            print("Transport booking tables created successfully!")
            
    except Exception as e:
        print(f"Error creating transport booking tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating transport booking tables...")
    success = create_transport_tables()
    
    if success:
        print("Transport booking system is ready!")
        print("\nNext steps:")
        print("1. Update your models/__init__.py to include the new models")
        print("2. Test the API endpoints")
        print("3. Create the frontend components")
    else:
        print("Failed to create transport booking tables")
        sys.exit(1)