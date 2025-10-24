#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.guesthouse import AccommodationAllocation
from app.models.event_participant import EventParticipant
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_existing_room_sharing():
    """Fix existing room assignments to implement sharing for same-gender participants"""
    
    db: Session = SessionLocal()
    
    try:
        # Find all single room allocations grouped by event and gender
        single_allocations = db.query(AccommodationAllocation).join(
            EventParticipant, AccommodationAllocation.participant_id == EventParticipant.id
        ).filter(
            AccommodationAllocation.room_type == 'single',
            AccommodationAllocation.number_of_guests == 1,
            AccommodationAllocation.status.in_(['booked', 'checked_in']),
            EventParticipant.gender.isnot(None)
        ).all()
        
        # Group by event_id and gender
        event_gender_groups = {}
        for allocation in single_allocations:
            key = (allocation.event_id, allocation.participant.gender)
            if key not in event_gender_groups:
                event_gender_groups[key] = []
            event_gender_groups[key].append(allocation)
        
        # Process groups with 2 or more participants
        for (event_id, gender), allocations in event_gender_groups.items():
            if len(allocations) >= 2:
                logger.info(f"Processing {len(allocations)} {gender} participants in event {event_id}")
                
                # Pair participants for room sharing
                for i in range(0, len(allocations), 2):
                    if i + 1 < len(allocations):
                        allocation1 = allocations[i]
                        allocation2 = allocations[i + 1]
                        
                        logger.info(f"Pairing participants {allocation1.participant_id} and {allocation2.participant_id}")
                        
                        # Update both allocations to double room
                        allocation1.room_type = 'double'
                        allocation1.number_of_guests = 2
                        allocation1.notes = f"Shared with participant {allocation2.participant_id} ({allocation2.guest_name})"
                        
                        allocation2.room_type = 'double'
                        allocation2.number_of_guests = 2
                        allocation2.notes = f"Shared with participant {allocation1.participant_id} ({allocation1.guest_name})"
                        
                        logger.info(f"Updated room sharing for {allocation1.guest_name} and {allocation2.guest_name}")
        
        db.commit()
        logger.info("Successfully updated existing room assignments with sharing logic")
        
    except Exception as e:
        logger.error(f"Error fixing room sharing: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_existing_room_sharing()