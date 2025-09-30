#!/usr/bin/env python3
"""
Create all event-related tables in correct order
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_events_tables():
    """Create all event tables in correct dependency order"""
    
    tables_sql = [
        # 1. Events table (base table)
        """
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            location VARCHAR(255),
            accommodation VARCHAR(255),
            room_info VARCHAR(500),
            food_details VARCHAR(500),
            rates DECIMAL(10,2),
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # 2. Event participants table
        """
        CREATE TABLE IF NOT EXISTS event_participants (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            email VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            status VARCHAR(20) DEFAULT 'invited',
            invited_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(event_id, email)
        )
        """,
        
        # 3. Event participant checklists table
        """
        CREATE TABLE IF NOT EXISTS event_participant_checklists (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            item VARCHAR(255) NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # 4. Event items table
        """
        CREATE TABLE IF NOT EXISTS event_items (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            item_name VARCHAR(255) NOT NULL,
            item_type VARCHAR(20) NOT NULL,
            description VARCHAR(500),
            total_quantity INTEGER NOT NULL DEFAULT 0,
            allocated_quantity INTEGER NOT NULL DEFAULT 0,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # 5. Participant allocations table
        """
        CREATE TABLE IF NOT EXISTS participant_allocations (
            id SERIAL PRIMARY KEY,
            event_item_id INTEGER NOT NULL REFERENCES event_items(id),
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            allocated_quantity INTEGER NOT NULL DEFAULT 1,
            redeemed_quantity INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(event_item_id, participant_id)
        )
        """,
        
        # 6. Redemption logs table
        """
        CREATE TABLE IF NOT EXISTS redemption_logs (
            id SERIAL PRIMARY KEY,
            allocation_id INTEGER NOT NULL REFERENCES participant_allocations(id),
            quantity_redeemed INTEGER NOT NULL,
            redeemed_by VARCHAR(255) NOT NULL,
            notes VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """,
        
        # 7. Extra item requests table
        """
        CREATE TABLE IF NOT EXISTS extra_item_requests (
            id SERIAL PRIMARY KEY,
            event_item_id INTEGER NOT NULL REFERENCES event_items(id),
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            requested_quantity INTEGER NOT NULL,
            reason VARCHAR(500),
            status VARCHAR(20) DEFAULT 'pending',
            approved_by VARCHAR(255),
            approved_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_events_tenant_id ON events(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date)",
        "CREATE INDEX IF NOT EXISTS idx_event_participants_event_id ON event_participants(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_participants_email ON event_participants(email)",
        "CREATE INDEX IF NOT EXISTS idx_event_items_event_id ON event_items(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_allocations_event_item_id ON participant_allocations(event_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_allocations_participant_id ON participant_allocations(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_redemption_logs_allocation_id ON redemption_logs(allocation_id)",
        "CREATE INDEX IF NOT EXISTS idx_extra_item_requests_event_item_id ON extra_item_requests(event_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_extra_item_requests_participant_id ON extra_item_requests(participant_id)"
    ]
    
    try:
        with engine.connect() as conn:
            # Create tables
            for i, sql in enumerate(tables_sql, 1):
                print(f"Creating table {i}/{len(tables_sql)}...")
                conn.execute(text(sql))
            
            # Create indexes
            for i, sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(sql))
            
            conn.commit()
            print("All event tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_events_tables()
    sys.exit(0 if success else 1)