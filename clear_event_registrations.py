#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clear_event_registrations(event_id):
    """Clear all registrations for a specific event"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Delete from public_registrations table first (if exists)
                result1 = conn.execute(text("""
                    DELETE FROM public_registrations 
                    WHERE event_id = :event_id
                """), {"event_id": event_id})
                
                # Delete from event_participants table
                result2 = conn.execute(text("""
                    DELETE FROM event_participants 
                    WHERE event_id = :event_id
                """), {"event_id": event_id})
                
                # Commit transaction
                trans.commit()
                
                print(f"SUCCESS: Cleared {result2.rowcount} participants from event {event_id}")
                print(f"SUCCESS: Cleared {result1.rowcount} detailed registrations from event {event_id}")
                return True
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e
        
    except Exception as e:
        print(f"ERROR: Failed to clear registrations: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clear_event_registrations.py <event_id>")
        print("Example: python clear_event_registrations.py 41")
        sys.exit(1)
    
    try:
        event_id = int(sys.argv[1])
    except ValueError:
        print("ERROR: Event ID must be a number")
        sys.exit(1)
    
    print(f"Clearing all registrations for event {event_id}...")
    
    # Confirm action
    confirm = input(f"Are you sure you want to delete ALL registrations for event {event_id}? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        sys.exit(0)
    
    success = clear_event_registrations(event_id)
    sys.exit(0 if success else 1)