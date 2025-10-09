#!/usr/bin/env python3
"""
Create airport pickup tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_airport_pickup_tables():
    """Create airport pickup and travel agent tables"""
    
    tables_sql = [
        # Travel agents table
        """
        CREATE TABLE IF NOT EXISTS travel_agents (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            phone VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            tenant_id VARCHAR(50) NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            api_token VARCHAR(255) UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Airport pickups table
        """
        CREATE TABLE IF NOT EXISTS airport_pickups (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id) UNIQUE,
            driver_name VARCHAR(255) NOT NULL,
            driver_phone VARCHAR(50) NOT NULL,
            driver_email VARCHAR(255),
            vehicle_details VARCHAR(255),
            pickup_time TIMESTAMP WITH TIME ZONE NOT NULL,
            destination VARCHAR(500) NOT NULL,
            special_instructions TEXT,
            travel_agent_email VARCHAR(255),
            driver_confirmed BOOLEAN DEFAULT FALSE,
            visitor_confirmed BOOLEAN DEFAULT FALSE,
            admin_confirmed BOOLEAN DEFAULT FALSE,
            welcome_package_confirmed BOOLEAN DEFAULT FALSE,
            pickup_completed BOOLEAN DEFAULT FALSE,
            driver_confirmation_time TIMESTAMP WITH TIME ZONE,
            visitor_confirmation_time TIMESTAMP WITH TIME ZONE,
            admin_confirmation_time TIMESTAMP WITH TIME ZONE,
            confirmed_by_admin VARCHAR(255),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_travel_agents_email ON travel_agents(email)",
        "CREATE INDEX IF NOT EXISTS idx_travel_agents_tenant_id ON travel_agents(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_travel_agents_api_token ON travel_agents(api_token)",
        "CREATE INDEX IF NOT EXISTS idx_airport_pickups_participant_id ON airport_pickups(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_airport_pickups_travel_agent_email ON airport_pickups(travel_agent_email)",
        "CREATE INDEX IF NOT EXISTS idx_airport_pickups_pickup_time ON airport_pickups(pickup_time)",
        "CREATE INDEX IF NOT EXISTS idx_airport_pickups_pickup_completed ON airport_pickups(pickup_completed)"
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
            print("Airport pickup tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_airport_pickup_tables()
    sys.exit(0 if success else 1)