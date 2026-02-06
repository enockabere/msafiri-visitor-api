from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/{event_id}/statistics")
def get_event_statistics(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get comprehensive event statistics including participant counts by role and status."""
    
    # Get total registered participants
    total_registered = db.query(func.count(EventParticipant.id)).filter(
        EventParticipant.event_id == event_id
    ).scalar() or 0
    
    # Get participants by status
    selected_count = db.query(func.count(EventParticipant.id)).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.status == 'selected'
    ).scalar() or 0
    
    waiting_count = db.query(func.count(EventParticipant.id)).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.status == 'registered'
    ).scalar() or 0
    
    attended_count = db.query(func.count(EventParticipant.id)).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.status == 'checked_in'
    ).scalar() or 0
    
    # Get participants by role - check both role and participant_role columns
    try:
        # Use raw SQL to handle both role columns
        facilitator_count = db.execute(
            text("""
                SELECT COUNT(*) FROM event_participants 
                WHERE event_id = :event_id 
                AND (role = 'facilitator' OR participant_role = 'facilitator')
            """),
            {"event_id": event_id}
        ).scalar() or 0
        
        organizer_count = db.execute(
            text("""
                SELECT COUNT(*) FROM event_participants 
                WHERE event_id = :event_id 
                AND (role = 'organizer' OR participant_role = 'organizer')
            """),
            {"event_id": event_id}
        ).scalar() or 0
        
        visitor_count = db.execute(
            text("""
                SELECT COUNT(*) FROM event_participants 
                WHERE event_id = :event_id 
                AND (role = 'visitor' OR participant_role = 'visitor' OR role IS NULL OR participant_role IS NULL)
            """),
            {"event_id": event_id}
        ).scalar() or 0
        
    except Exception as e:
        # Fallback to just role column if participant_role doesn't exist
        facilitator_count = db.query(func.count(EventParticipant.id)).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.role == 'facilitator'
        ).scalar() or 0
        
        organizer_count = db.query(func.count(EventParticipant.id)).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.role == 'organizer'
        ).scalar() or 0
        
        visitor_count = db.query(func.count(EventParticipant.id)).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.role.in_(['visitor', 'attendee'])
        ).scalar() or 0
    
    return {
        "event_id": event_id,
        "participants": {
            "registered": total_registered,
            "selected": selected_count,
            "waiting": waiting_count,
            "attended": attended_count
        },
        "roles": {
            "facilitators": facilitator_count,
            "organizers": organizer_count,
            "visitors": visitor_count
        }
    }
