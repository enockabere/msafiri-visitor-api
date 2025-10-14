from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from app.schemas.event_participant import EventParticipantCreate, EventParticipantUpdate

router = APIRouter()

@router.post("/", response_model=schemas.event_participant.EventParticipant, operation_id="create_event_participant")
def create_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_in: EventParticipantCreate
) -> Any:
    """Create new event participant"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if participant already exists
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == participant_in.email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Participant already exists for this event")
    
    # Create participant
    participant = EventParticipant(
        event_id=event_id,
        full_name=participant_in.full_name,
        email=participant_in.email,
        role=getattr(participant_in, 'role', 'attendee'),
        status='invited',
        invited_by='admin'
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    return participant

@router.get("/", response_model=List[schemas.event_participant.EventParticipant], operation_id="get_event_participants")
def get_participants(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    role: str = None,
    skip: int = 0,
    limit: int = 50
) -> Any:
    """Get event participants with optional role filtering and pagination"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🎯 Get participants - Event: {event_id}, Role filter: {role}")
    
    query = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    )
    
    if role:
        # Check both role and participant_role columns
        from sqlalchemy import or_, text
        try:
            # Try to filter by both role and participant_role columns
            query = query.filter(
                or_(
                    EventParticipant.role == role,
                    text(f"participant_role = '{role}'")
                )
            )
            logger.info(f"✅ Applied role filter for both 'role' and 'participant_role' columns")
        except Exception as e:
            # Fallback to just role column if participant_role doesn't exist
            logger.warning(f"⚠️ participant_role column might not exist, using only role column: {e}")
            query = query.filter(EventParticipant.role == role)
    
    participants = query.offset(skip).limit(limit).all()
    logger.info(f"📊 Found {len(participants)} participants")
    
    return participants

@router.put("/{participant_id}/role")
async def update_participant_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    role_data: dict
) -> Any:
    """Update participant role"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Validate role
    valid_roles = ['visitor', 'facilitator', 'organizer']
    new_role = role_data.get('role', '').lower()
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    old_role = getattr(participant, 'participant_role', 'visitor')
    
    # Update participant_role using raw SQL if column exists
    try:
        from sqlalchemy import text
        db.execute(
            text("UPDATE event_participants SET participant_role = :role WHERE id = :id"),
            {"role": new_role, "id": participant_id}
        )
        db.commit()
        
        # Send role change notification email
        if old_role != new_role:
            await send_role_change_notification(participant, old_role, new_role, db)
        
        return {"message": "Role updated successfully", "new_role": new_role}
        
    except Exception as e:
        db.rollback()
        print(f"Error updating participant role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role")

async def send_role_change_notification(participant, old_role, new_role, db):
    """Send email notification when participant role changes"""
    try:
        if not participant.email or not participant.email.strip():
            return False
        
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            return False
        
        from app.core.email_service import email_service
        
        subject = f"Role Updated - {event.title}"
        
        role_descriptions = {
            'visitor': 'Event Participant',
            'facilitator': 'Event Facilitator', 
            'organizer': 'Event Organizer'
        }
        
        message = f"""
        <p>Dear {participant.full_name},</p>
        <p>Your role for <strong>{event.title}</strong> has been updated.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #f0f9ff; border-left: 4px solid #3b82f6;">
            <h3>Role Change Details:</h3>
            <p><strong>Event:</strong> {event.title}</p>
            <p><strong>Previous Role:</strong> {role_descriptions.get(old_role, old_role.title())}</p>
            <p><strong>New Role:</strong> {role_descriptions.get(new_role, new_role.title())}</p>
        </div>
        
        <p>Please check the Msafiri mobile app for any updated responsibilities or information related to your new role.</p>
        """
        
        return email_service.send_notification_email(
            to_email=participant.email,
            user_name=participant.full_name,
            title=subject,
            message=message
        )
        
    except Exception as e:
        print(f"Error sending role change notification: {e}")
        return False

@router.delete("/{participant_id}", operation_id="delete_event_participant")
def delete_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int
) -> Any:
    """Delete event participant"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    db.delete(participant)
    db.commit()
    
    return {"message": "Participant deleted successfully"}