#!/usr/bin/env python3
"""
Create event attendance tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_event_attendance_tables():
    """Create event attendance and review tables"""
    
    tables_sql = [
        # Event check-ins table
        """
        CREATE TABLE IF NOT EXISTS event_checkins (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            event_id INTEGER NOT NULL REFERENCES events(id),
            checkin_date DATE NOT NULL,
            checkin_time TIMESTAMP WITH TIME ZONE NOT NULL,
            checked_in_by VARCHAR(255) NOT NULL,
            qr_token_used VARCHAR(255) NOT NULL,
            badge_printed BOOLEAN DEFAULT FALSE,
            badge_printed_at TIMESTAMP WITH TIME ZONE,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, event_id, checkin_date)
        )
        """,
        
        # Equipment requests table
        """
        CREATE TABLE IF NOT EXISTS equipment_requests (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            event_id INTEGER NOT NULL REFERENCES events(id),
            equipment_name VARCHAR(255) NOT NULL,
            quantity INTEGER DEFAULT 1,
            description TEXT,
            urgency VARCHAR(20) DEFAULT 'normal',
            status VARCHAR(20) DEFAULT 'pending',
            admin_notes TEXT,
            approved_by VARCHAR(255),
            fulfilled_by VARCHAR(255),
            fulfilled_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Event reviews table
        """
        CREATE TABLE IF NOT EXISTS event_reviews (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            event_id INTEGER NOT NULL REFERENCES events(id),
            overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
            content_rating INTEGER CHECK (content_rating >= 1 AND content_rating <= 5),
            organization_rating INTEGER CHECK (organization_rating >= 1 AND organization_rating <= 5),
            venue_rating INTEGER CHECK (venue_rating >= 1 AND venue_rating <= 5),
            catering_rating INTEGER CHECK (catering_rating >= 1 AND catering_rating <= 5),
            review_text TEXT,
            suggestions TEXT,
            would_recommend BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, event_id)
        )
        """,
        
        # App reviews table
        """
        CREATE TABLE IF NOT EXISTS app_reviews (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
            ease_of_use INTEGER CHECK (ease_of_use >= 1 AND ease_of_use <= 5),
            functionality_rating INTEGER CHECK (functionality_rating >= 1 AND functionality_rating <= 5),
            design_rating INTEGER CHECK (design_rating >= 1 AND design_rating <= 5),
            review_text TEXT,
            suggestions TEXT,
            device_type VARCHAR(50),
            app_version VARCHAR(20),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(user_email)
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_event_checkins_participant_id ON event_checkins(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_checkins_event_id ON event_checkins(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_checkins_checkin_date ON event_checkins(checkin_date)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_requests_participant_id ON equipment_requests(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_requests_event_id ON equipment_requests(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_requests_status ON equipment_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_event_reviews_event_id ON event_reviews(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_reviews_overall_rating ON event_reviews(overall_rating)",
        "CREATE INDEX IF NOT EXISTS idx_app_reviews_overall_rating ON app_reviews(overall_rating)",
        "CREATE INDEX IF NOT EXISTS idx_app_reviews_user_email ON app_reviews(user_email)"
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
            print("Event attendance tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_event_attendance_tables()
    sys.exit(0 if success else 1)