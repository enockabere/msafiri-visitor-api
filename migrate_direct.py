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