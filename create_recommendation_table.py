#!/usr/bin/env python3
"""
Create line manager recommendations table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def create_recommendation_table():
    """Create line_manager_recommendations table"""
    
    print("Creating line_manager_recommendations table...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS line_manager_recommendations (
                    id SERIAL PRIMARY KEY,
                    registration_id INTEGER REFERENCES public_registrations(id) ON DELETE CASCADE,
                    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                    participant_name VARCHAR(255) NOT NULL,
                    participant_email VARCHAR(255) NOT NULL,
                    line_manager_email VARCHAR(255) NOT NULL,
                    operation_center VARCHAR(50),
                    event_title VARCHAR(255),
                    event_dates VARCHAR(100),
                    event_location VARCHAR(255),
                    recommendation_token VARCHAR(255) UNIQUE NOT NULL,
                    recommendation_text TEXT,
                    submitted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create index for faster lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_recommendations_token 
                ON line_manager_recommendations(recommendation_token)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_recommendations_event_id 
                ON line_manager_recommendations(event_id)
            """))
            
            conn.commit()
            print("✅ line_manager_recommendations table created successfully")
            
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            conn.rollback()

if __name__ == "__main__":
    create_recommendation_table()