#!/usr/bin/env python3
"""
Create event transport tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_event_transport_tables():
    """Create event transportation tables"""
    
    tables_sql = [
        # Event rides table
        """
        CREATE TABLE IF NOT EXISTS event_rides (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            departure_location VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
            driver_name VARCHAR(255) NOT NULL,
            driver_phone VARCHAR(50) NOT NULL,
            vehicle_details VARCHAR(255),
            max_capacity INTEGER NOT NULL DEFAULT 4,
            current_occupancy INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            special_instructions TEXT,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Ride assignments table
        """
        CREATE TABLE IF NOT EXISTS ride_assignments (
            id SERIAL PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES event_rides(id),
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            pickup_location VARCHAR(255),
            pickup_time TIMESTAMP WITH TIME ZONE,
            confirmed BOOLEAN DEFAULT FALSE,
            boarded BOOLEAN DEFAULT FALSE,
            assigned_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, ride_id)
        )
        """,
        
        # Ride requests table
        """
        CREATE TABLE IF NOT EXISTS ride_requests (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            event_id INTEGER NOT NULL REFERENCES events(id),
            pickup_location VARCHAR(255) NOT NULL,
            preferred_time TIMESTAMP WITH TIME ZONE NOT NULL,
            special_requirements TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            admin_notes TEXT,
            approved_by VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_event_rides_event_id ON event_rides(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_rides_departure_time ON event_rides(departure_time)",
        "CREATE INDEX IF NOT EXISTS idx_event_rides_status ON event_rides(status)",
        "CREATE INDEX IF NOT EXISTS idx_ride_assignments_ride_id ON ride_assignments(ride_id)",
        "CREATE INDEX IF NOT EXISTS idx_ride_assignments_participant_id ON ride_assignments(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_ride_requests_participant_id ON ride_requests(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_ride_requests_event_id ON ride_requests(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_ride_requests_status ON ride_requests(status)"
    ]
    
    try:
        with engine.connect() as conn:
            for i, sql in enumerate(tables_sql, 1):
                print(f"Creating table {i}/{len(tables_sql)}...")
                conn.execute(text(sql))
            
            for i, sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(sql))
            
            conn.commit()
            print("Event transport tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_event_transport_tables()
    sys.exit(0 if success else 1)