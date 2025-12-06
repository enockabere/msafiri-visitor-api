#!/usr/bin/env python3
"""
Script to manually create the transport_requests table if it doesn't exist.
This is a one-time fix for production database.
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://msafiri_user:password%401234@localhost:5432/msafiri_db"
)

def create_transport_requests_table():
    """Create transport_requests table if it doesn't exist."""

    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    # Check if table already exists
    if 'transport_requests' in inspector.get_table_names():
        print("✅ transport_requests table already exists!")
        return

    print("📋 Creating transport_requests table...")

    # SQL to create the table
    create_table_sql = """
    CREATE TABLE transport_requests (
        id SERIAL PRIMARY KEY,
        pickup_address VARCHAR(500) NOT NULL,
        pickup_latitude FLOAT,
        pickup_longitude FLOAT,
        dropoff_address VARCHAR(500) NOT NULL,
        dropoff_latitude FLOAT,
        dropoff_longitude FLOAT,
        pickup_time TIMESTAMP NOT NULL,
        passenger_name VARCHAR(255) NOT NULL,
        passenger_phone VARCHAR(50) NOT NULL,
        passenger_email VARCHAR(255),
        vehicle_type VARCHAR(100),
        flight_details VARCHAR(255),
        notes TEXT,
        event_id INTEGER NOT NULL REFERENCES events(id),
        flight_itinerary_id INTEGER REFERENCES flight_itineraries(id),
        user_email VARCHAR(255) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        driver_name VARCHAR(255),
        driver_phone VARCHAR(50),
        vehicle_number VARCHAR(50),
        vehicle_color VARCHAR(50),
        booking_reference VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX idx_transport_requests_event_id ON transport_requests(event_id);
    CREATE INDEX idx_transport_requests_flight_itinerary_id ON transport_requests(flight_itinerary_id);
    CREATE INDEX idx_transport_requests_user_email ON transport_requests(user_email);
    CREATE INDEX idx_transport_requests_status ON transport_requests(status);
    """

    try:
        with engine.connect() as conn:
            # Execute the SQL
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ Successfully created transport_requests table with all columns and indexes!")

    except Exception as e:
        print(f"❌ Error creating table: {str(e)}")
        sys.exit(1)

    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🚀 Transport Requests Table Creation Script")
    print("=" * 50)
    create_transport_requests_table()
    print("=" * 50)
    print("✅ Done!")
