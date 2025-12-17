#!/usr/bin/env python3
"""
Script to update test participant emails for notification testing
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/msafiri_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_participant_emails():
    """Update some participant emails for testing notifications"""
    
    test_emails = [
        "maebaeneock95@gmail.com",
        "abereenock95@gmail.com", 
        "msafiriapp@proton.me",
        "enockmaeba@yahoo.com"
    ]
    
    db = SessionLocal()
    try:
        # Get participants with different statuses
        participants = db.execute(text("""
            SELECT id, email, status, full_name 
            FROM event_participants 
            WHERE status IN ('selected', 'waiting', 'not_selected', 'confirmed')
            ORDER BY id 
            LIMIT 4
        """)).fetchall()
        
        if len(participants) < 4:
            print(f"Only found {len(participants)} participants. Need at least 4.")
            return
        
        print("Updating participant emails for notification testing:")
        print("-" * 60)
        
        for i, participant in enumerate(participants):
            old_email = participant.email
            new_email = test_emails[i]
            
            # Update participant email
            db.execute(text("""
                UPDATE event_participants 
                SET email = :new_email 
                WHERE id = :participant_id
            """), {
                "new_email": new_email,
                "participant_id": participant.id
            })
            
            print(f"ID {participant.id}: {participant.full_name}")
            print(f"  Status: {participant.status}")
            print(f"  Email: {old_email} -> {new_email}")
            print()
        
        db.commit()
        print("Email updates completed successfully!")
        print("\nNow when you approve vetting, notifications will be sent to these emails.")
        
    except Exception as e:
        db.rollback()
        print(f"Error updating emails: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_participant_emails()