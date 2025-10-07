#!/usr/bin/env python3
"""
Direct SQL migration script for Msafiri Visitor API
Adds missing columns directly to the database
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_direct_migration():
    """Run direct SQL migration"""
    try:
        logger.info("🔄 Starting direct database migration...")
        
        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Add columns to users table (if they don't exist)
                user_columns = [
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR(255)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS project VARCHAR(255)"
                ]
                
                for sql in user_columns:
                    logger.info(f"Executing: {sql}")
                    conn.execute(text(sql))
                
                # Add columns to event_participants table (if they don't exist)
                participant_columns = [
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS position VARCHAR(255)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS project VARCHAR(255)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS gender VARCHAR(50)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS eta VARCHAR(255)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS requires_eta BOOLEAN DEFAULT FALSE",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS passport_document VARCHAR(500)",
                    "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS ticket_document VARCHAR(500)"
                ]
                
                for sql in participant_columns:
                    logger.info(f"Executing: {sql}")
                    conn.execute(text(sql))
                
                # Add column to events table (if it doesn't exist)
                event_columns = [
                    "ALTER TABLE events ADD COLUMN IF NOT EXISTS country VARCHAR(100)"
                ]
                
                for sql in event_columns:
                    logger.info(f"Executing: {sql}")
                    conn.execute(text(sql))
                
                # Create event_agenda table (if it doesn't exist)
                create_agenda_table = """
                CREATE TABLE IF NOT EXISTS event_agenda (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    day_number INTEGER NOT NULL,
                    event_date DATE NOT NULL,
                    time VARCHAR(10) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
                
                logger.info("Creating event_agenda table...")
                conn.execute(text(create_agenda_table))
                
                # Add unique constraints
                unique_constraints = [
                    "ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS users_email_unique UNIQUE (email)",
                    "ALTER TABLE events ADD CONSTRAINT IF NOT EXISTS events_title_unique UNIQUE (title)"
                ]
                
                for sql in unique_constraints:
                    logger.info(f"Executing: {sql}")
                    conn.execute(text(sql))
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Direct migration completed successfully!")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"❌ Direct migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_direct_migration()