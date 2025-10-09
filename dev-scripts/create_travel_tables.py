#!/usr/bin/env python3
"""
Create travel management tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_travel_tables():
    """Create travel management tables"""
    
    tables_sql = [
        # Participant tickets table
        """
        CREATE TABLE IF NOT EXISTS participant_tickets (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id) UNIQUE,
            departure_date DATE NOT NULL,
            arrival_date DATE NOT NULL,
            departure_airport VARCHAR(100) NOT NULL,
            arrival_airport VARCHAR(100) NOT NULL,
            flight_number VARCHAR(50),
            airline VARCHAR(100),
            ticket_reference VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Event welcome packages table
        """
        CREATE TABLE IF NOT EXISTS event_welcome_packages (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            item_name VARCHAR(255) NOT NULL,
            description TEXT,
            quantity_per_participant INTEGER DEFAULT 1,
            is_functional_phone BOOLEAN DEFAULT FALSE,
            pickup_instructions TEXT,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Participant welcome deliveries table
        """
        CREATE TABLE IF NOT EXISTS participant_welcome_deliveries (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            package_item_id INTEGER NOT NULL REFERENCES event_welcome_packages(id),
            delivered BOOLEAN DEFAULT FALSE,
            delivered_by VARCHAR(255),
            delivery_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, package_item_id)
        )
        """,
        
        # Event travel requirements table
        """
        CREATE TABLE IF NOT EXISTS event_travel_requirements (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            requirement_type VARCHAR(20) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            is_mandatory BOOLEAN DEFAULT TRUE,
            deadline_days_before INTEGER,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Participant requirement status table
        """
        CREATE TABLE IF NOT EXISTS participant_requirement_status (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            requirement_id INTEGER NOT NULL REFERENCES event_travel_requirements(id),
            completed BOOLEAN DEFAULT FALSE,
            completion_notes TEXT,
            completed_by VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, requirement_id)
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_participant_tickets_participant_id ON participant_tickets(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_welcome_packages_event_id ON event_welcome_packages(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_welcome_deliveries_participant_id ON participant_welcome_deliveries(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_travel_requirements_event_id ON event_travel_requirements(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_requirement_status_participant_id ON participant_requirement_status(participant_id)"
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
            print("Travel management tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_travel_tables()
    sys.exit(0 if success else 1)