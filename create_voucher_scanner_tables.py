#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_voucher_scanner_tables():
    """Create tables for voucher scanner functionality"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        # Start transaction
        trans = connection.begin()
        
        try:
            print("Creating voucher scanner tables...")
            
            # Update participant_voucher_redemptions table structure
            print("Updating participant_voucher_redemptions table...")
            
            # Check if table exists and get current structure
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'participant_voucher_redemptions'
                ORDER BY ordinal_position;
            """))
            
            existing_columns = {row[0]: row[1] for row in result.fetchall()}
            
            if existing_columns:
                print("Table exists, checking for required columns...")
                
                # Add missing columns if needed
                if 'event_id' not in existing_columns:
                    connection.execute(text("""
                        ALTER TABLE participant_voucher_redemptions 
                        ADD COLUMN event_id INTEGER REFERENCES events(id);
                    """))
                    print("Added event_id column")
                
                if 'location' not in existing_columns:
                    connection.execute(text("""
                        ALTER TABLE participant_voucher_redemptions 
                        ADD COLUMN location VARCHAR(255);
                    """))
                    print("Added location column")
                
                # Update redeemed_by to be integer if it's currently string
                if existing_columns.get('redeemed_by') == 'character varying':
                    connection.execute(text("""
                        ALTER TABLE participant_voucher_redemptions 
                        ADD COLUMN redeemed_by_user_id INTEGER REFERENCES users(id);
                    """))
                    print("Added redeemed_by_user_id column")
                
                # Update participant_id to reference users directly if needed
                participant_id_type = existing_columns.get('participant_id')
                if participant_id_type:
                    # Check if it references event_participants or users
                    fk_result = connection.execute(text("""
                        SELECT 
                            tc.constraint_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY' 
                            AND tc.table_name = 'participant_voucher_redemptions'
                            AND kcu.column_name = 'participant_id';
                    """))
                    
                    fk_info = fk_result.fetchone()
                    if fk_info and fk_info[1] != 'users':
                        print(f"participant_id currently references {fk_info[1]}, adding user_id column...")
                        connection.execute(text("""
                            ALTER TABLE participant_voucher_redemptions 
                            ADD COLUMN user_id INTEGER REFERENCES users(id);
                        """))
                        print("Added user_id column")
            
            else:
                print("Creating new participant_voucher_redemptions table...")
                connection.execute(text("""
                    CREATE TABLE participant_voucher_redemptions (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        participant_id INTEGER NOT NULL REFERENCES users(id),
                        redeemed_by INTEGER NOT NULL REFERENCES users(id),
                        redeemed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        location VARCHAR(255),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                print("Created participant_voucher_redemptions table")
            
            # Create indexes for better performance
            print("Creating indexes...")
            
            try:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_voucher_redemptions_event_participant 
                    ON participant_voucher_redemptions(event_id, participant_id);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_voucher_redemptions_redeemed_at 
                    ON participant_voucher_redemptions(redeemed_at);
                """))
                
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_voucher_redemptions_scanner 
                    ON participant_voucher_redemptions(redeemed_by);
                """))
                
                print("Created indexes successfully")
            except Exception as e:
                print(f"Note: Some indexes may already exist: {e}")
            
            # Ensure voucher_scanner role exists
            print("Ensuring voucher_scanner role exists...")
            
            # Check if role exists
            role_result = connection.execute(text("""
                SELECT id FROM roles WHERE name = 'voucher_scanner' LIMIT 1;
            """))
            
            if not role_result.fetchone():
                connection.execute(text("""
                    INSERT INTO roles (name, description, created_at, updated_at)
                    VALUES ('voucher_scanner', 'Can scan and redeem vouchers', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """))
                print("Created voucher_scanner role")
            else:
                print("voucher_scanner role already exists")
            
            # Commit transaction
            trans.commit()
            print("✅ All voucher scanner tables created successfully!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"❌ Error creating tables: {e}")
            raise e

if __name__ == "__main__":
    create_voucher_scanner_tables()