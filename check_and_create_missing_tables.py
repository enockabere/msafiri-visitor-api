#!/usr/bin/env python3
"""
Script to check for and create missing tables in the database.
This handles the case where migrations weren't fully applied.
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://msafiri_user:password%401234@localhost:5432/msafiri_db"
)

def create_flight_itineraries_table(conn):
    """Create flight_itineraries table if it doesn't exist."""
    print("📋 Creating flight_itineraries table...")

    create_table_sql = """
    CREATE TABLE flight_itineraries (
        id SERIAL PRIMARY KEY,
        event_id INTEGER NOT NULL REFERENCES events(id),
        user_email VARCHAR(255) NOT NULL,
        departure_city VARCHAR(255),
        arrival_city VARCHAR(255),
        departure_date TIMESTAMP,
        departure_time VARCHAR(50),
        arrival_date TIMESTAMP,
        arrival_time VARCHAR(50),
        flight_number VARCHAR(100),
        airline VARCHAR(255),
        booking_reference VARCHAR(100),
        ticket_number VARCHAR(100),
        cabin_class VARCHAR(50),
        seat_number VARCHAR(20),
        baggage_allowance VARCHAR(100),
        special_requests TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        confirmation_date TIMESTAMP,
        ticket_attachment VARCHAR(500),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        destination VARCHAR(255)
    );

    CREATE INDEX idx_flight_itineraries_event_id ON flight_itineraries(event_id);
    CREATE INDEX idx_flight_itineraries_user_email ON flight_itineraries(user_email);
    CREATE INDEX idx_flight_itineraries_status ON flight_itineraries(status);
    """

    conn.execute(text(create_table_sql))
    print("✅ Successfully created flight_itineraries table!")

def create_transport_requests_table(conn):
    """Create transport_requests table if it doesn't exist."""
    print("📋 Creating transport_requests table...")

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

    CREATE INDEX idx_transport_requests_event_id ON transport_requests(event_id);
    CREATE INDEX idx_transport_requests_flight_itinerary_id ON transport_requests(flight_itinerary_id);
    CREATE INDEX idx_transport_requests_user_email ON transport_requests(user_email);
    CREATE INDEX idx_transport_requests_status ON transport_requests(status);
    """

    conn.execute(text(create_table_sql))
    print("✅ Successfully created transport_requests table!")

def check_and_create_tables():
    """Check for missing tables and create them."""

    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    print(f"📊 Found {len(existing_tables)} existing tables in database")

    tables_to_check = {
        'flight_itineraries': create_flight_itineraries_table,
        'transport_requests': create_transport_requests_table,
    }

    missing_tables = []
    for table_name in tables_to_check.keys():
        if table_name not in existing_tables:
            missing_tables.append(table_name)

    if not missing_tables:
        print("✅ All required tables already exist!")
        return

    print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
    print("\n🔧 Creating missing tables in the correct order...\n")

    try:
        with engine.connect() as conn:
            # Create tables in dependency order
            for table_name, create_func in tables_to_check.items():
                if table_name in missing_tables:
                    create_func(conn)

            conn.commit()
            print("\n✅ All missing tables created successfully!")

    except Exception as e:
        print(f"\n❌ Error creating tables: {str(e)}")
        print("\nFull error details:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        engine.dispose()

def main():
    print("=" * 60)
    print("🚀 Database Tables Check and Creation Script")
    print("=" * 60)
    print()

    try:
        check_and_create_tables()
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("=" * 60)
    print("✅ Script completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
