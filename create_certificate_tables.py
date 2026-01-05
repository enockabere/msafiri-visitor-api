#!/usr/bin/env python3
"""
Create certificate and badge tables for the mobile app certificate system.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from production .env
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'msafiri_db')
DB_USER = os.getenv('POSTGRES_USER', 'msafiri_user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password@1234')

def create_certificate_tables():
    """Create all certificate and badge related tables."""
    
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    try:
        print("Creating certificate and badge tables...")
        
        # 1. Certificate Templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificate_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                template_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("[OK] Created certificate_templates table")
        
        # 2. Badge Templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS badge_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                template_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("[OK] Created badge_templates table")
        
        # 3. Event Certificates table (links events to certificate templates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_certificates (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                certificate_template_id INTEGER NOT NULL REFERENCES certificate_templates(id) ON DELETE CASCADE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, certificate_template_id)
            );
        """)
        print("[OK] Created event_certificates table")
        
        # 4. Event Badges table (links events to badge templates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_badges (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                badge_template_id INTEGER NOT NULL REFERENCES badge_templates(id) ON DELETE CASCADE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, badge_template_id)
            );
        """)
        print("[OK] Created event_badges table")
        
        # 5. Participant Certificates table (generated certificates for participants)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participant_certificates (
                id SERIAL PRIMARY KEY,
                participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
                event_certificate_id INTEGER NOT NULL REFERENCES event_certificates(id) ON DELETE CASCADE,
                certificate_url VARCHAR(500),
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(participant_id, event_certificate_id)
            );
        """)
        print("[OK] Created participant_certificates table")
        
        # 6. Participant Badges table (generated badges for participants)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participant_badges (
                id SERIAL PRIMARY KEY,
                participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
                event_badge_id INTEGER NOT NULL REFERENCES event_badges(id) ON DELETE CASCADE,
                badge_url VARCHAR(500),
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(participant_id, event_badge_id)
            );
        """)
        print("[OK] Created participant_badges table")
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_certificates_event_id ON event_certificates(event_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_badges_event_id ON event_badges(event_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_participant_certificates_participant_id ON participant_certificates(participant_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_participant_badges_participant_id ON participant_badges(participant_id);")
        print("[OK] Created indexes")
        
        print("\n[SUCCESS] All certificate and badge tables created successfully!")
        
    except Exception as e:
        print("[ERROR] Error creating tables:", e)
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_certificate_tables()