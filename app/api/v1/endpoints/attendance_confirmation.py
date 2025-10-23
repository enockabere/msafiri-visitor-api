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

@router.post("/decline/{participant_id}")
async def decline_attendance(
    participant_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Decline attendance for participant with reason"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    if participant.status not in ["selected", "confirmed"]:
        raise HTTPException(status_code=400, detail="Only selected or confirmed participants can decline attendance")
    
    decline_reason = request_data.get("reason", "").strip()
    if not decline_reason:
        raise HTTPException(status_code=400, detail="Decline reason is required")
    
    # Update status to declined with reason and timestamp
    participant.status = "declined"
    participant.decline_reason = decline_reason
    participant.declined_at = datetime.utcnow()
    
    # Cancel any existing accommodation bookings
    try:
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        for allocation in existing_allocations:
            logger.info(f"Cancelling allocation {allocation.id} for declined participant")
            
            # Restore room counts
            if allocation.vendor_accommodation_id:
                if allocation.room_type == 'single':
                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET single_rooms = single_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
                elif allocation.room_type == 'double':
                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET double_rooms = double_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
            
            allocation.status = "cancelled"
            allocation.cancelled_reason = "Participant declined attendance"
    
    except Exception as e:
        logger.error(f"Error cancelling accommodations: {str(e)}")
    
    db.commit()
    
    # Send decline notification email
    try:
        await send_decline_notification(participant, decline_reason, db)
    except Exception as e:
        logger.error(f"Error sending decline notification: {str(e)}")
    
    return {
        "message": "Attendance declined successfully",
        "warning": "Your registration details will be deleted in 24 hours"
    }

async def send_decline_notification(participant, decline_reason, db):
    """Send email notification when participant declines"""
    try:
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            return False
        
        from app.core.email_service import email_service
        
        subject = f"Attendance Declined - {event.title}"
        
        message = f"""
        <p>Dear {participant.full_name},</p>
        <p>We have received your decline for <strong>{event.title}</strong>.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #fef2f2; border-left: 4px solid #ef4444;">
            <h3>Decline Details:</h3>
            <p><strong>Event:</strong> {event.title}</p>
            <p><strong>Reason:</strong> {decline_reason}</p>
            <p><strong>Declined At:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>
        
        <div style="margin: 20px 0; padding: 15px; background-color: #fff3cd; border: 1px solid #ffeaa7;">
            <p><strong>Important Notice:</strong> Your registration details will be automatically deleted in 24 hours. Any accommodation bookings have been cancelled.</p>
        </div>
        
        <p>Thank you for your time and consideration.</p>
        """
        
        return email_service.send_notification_email(
            to_email=participant.email,
            user_name=participant.full_name,
            title=subject,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error sending decline notification: {e}")
        return False