# File: app/api/v1/endpoints/attendance_confirmation.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from app.models.event import Event
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
    
    # Update status to confirmed
    participant.status = "confirmed"
    db.commit()
    
    # Trigger auto-booking for confirmed participant
    try:
        from app.api.v1.endpoints.auto_booking import _auto_book_participant_internal
        from app.models.user import User
        
        # Create a mock user for auto-booking (system user)
        class MockUser:
            def __init__(self):
                self.id = 1
                self.tenant_id = None
                self.email = "system@msf.org"
        
        mock_user = MockUser()
        tenant_context = "system"
        
        booking_result = _auto_book_participant_internal(
            event_id=participant.event_id,
            participant_id=participant.id,
            db=db,
            current_user=mock_user,
            tenant_context=tenant_context
        )
        
        return {
            "message": "Attendance confirmed successfully",
            "auto_booking": booking_result
        }
        
    except Exception as e:
        print(f"Auto-booking failed for participant {participant_id}: {str(e)}")
        return {
            "message": "Attendance confirmed successfully",
            "auto_booking_error": str(e)
        }