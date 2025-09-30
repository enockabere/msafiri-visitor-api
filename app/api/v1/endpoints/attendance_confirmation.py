# File: app/api/v1/endpoints/attendance_confirmation.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from app.models.event import Event
from datetime import datetime

router = APIRouter()

@router.get("/confirm/{participant_id}")
async def confirm_attendance_page(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Display confirmation page for participant"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    return {
        "participant": {
            "id": participant.id,
            "full_name": participant.full_name,
            "email": participant.email,
            "status": participant.status
        },
        "event": {
            "id": event.id,
            "title": event.title,
            "start_date": event.start_date,
            "end_date": event.end_date,
            "location": event.location
        }
    }

@router.post("/confirm/{participant_id}")
async def confirm_attendance(
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Confirm attendance for participant"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    if participant.status != "selected":
        raise HTTPException(status_code=400, detail="Only selected participants can confirm attendance")
    
    # Update status to confirmed and mark invitation as accepted
    participant.status = "confirmed"
    # participant.invitation_accepted = True
    # participant.invitation_accepted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Attendance confirmed successfully"}