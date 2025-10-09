#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_feedback_table():
    """Create event feedback table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS event_feedback (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    participant_id INTEGER REFERENCES event_participants(id) ON DELETE SET NULL,
                    participant_email VARCHAR(255) NOT NULL,
                    participant_name VARCHAR(255) NOT NULL,
                    overall_rating FLOAT NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
                    content_rating FLOAT CHECK (content_rating >= 1 AND content_rating <= 5),
                    organization_rating FLOAT CHECK (organization_rating >= 1 AND organization_rating <= 5),
                    venue_rating FLOAT CHECK (venue_rating >= 1 AND venue_rating <= 5),
                    feedback_text TEXT,
                    suggestions TEXT,
                    would_recommend VARCHAR(10) CHECK (would_recommend IN ('Yes', 'No', 'Maybe')),
                    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(event_id, participant_email)
                );
                
                CREATE INDEX IF NOT EXISTS idx_event_feedback_event_id ON event_feedback(event_id);
                CREATE INDEX IF NOT EXISTS idx_event_feedback_participant_email ON event_feedback(participant_email);
            """))
            connection.commit()
            print('Event feedback table created successfully!')
            
    except Exception as e:
        print(f"Error creating table: {str(e)}")

if __name__ == "__main__":
    create_feedback_table()