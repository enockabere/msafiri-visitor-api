from typing import Any, List, Dict
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

@router.get("/", operation_id="get_event_participants")
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
    
    # Enrich participants with registration data
    from app.models.public_registration import PublicRegistration
    enriched_participants = []
    
    logger.info(f"🔍 Enriching {len(participants)} participants with registration data")
    
    for participant in participants:
        logger.info(f"👤 Processing participant: {participant.full_name} ({participant.email})")
        
        # Get registration data
        registration = db.query(PublicRegistration).filter(
            PublicRegistration.event_id == event_id,
            PublicRegistration.email == participant.email
        ).first()
        
        if registration:
            logger.info(f"✅ Found registration for {participant.email}: gender={registration.gender}, accommodation_needs={registration.accommodation_needs}")
        else:
            logger.warning(f"❌ No registration found for {participant.email} in event {event_id}")
            # Try to find any registration for this email
            any_registration = db.query(PublicRegistration).filter(
                PublicRegistration.email == participant.email
            ).first()
            if any_registration:
                logger.info(f"📋 Found registration for {participant.email} in different event {any_registration.event_id}")
        
        # Create participant dict with additional fields
        participant_dict = {
            "id": participant.id,
            "event_id": participant.event_id,
            "full_name": participant.full_name,
            "email": participant.email,
            "role": participant.role,
            "status": participant.status,
            "gender": registration.gender if registration else None,
            "accommodation_needs": registration.accommodation_needs if registration else None
        }
        
        # Add participant_role if it exists
        try:
            from sqlalchemy import text
            result = db.execute(
                text("SELECT participant_role FROM event_participants WHERE id = :id"),
                {"id": participant.id}
            ).first()
            if result and result[0]:
                participant_dict["participant_role"] = result[0]
        except:
            pass
        
        logger.info(f"📦 Final participant data: {participant_dict}")
        enriched_participants.append(participant_dict)
    
    logger.info(f"🎯 Returning {len(enriched_participants)} enriched participants")
    return enriched_participants

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

@router.get("/{participant_id}/details", operation_id="get_participant_details")
def get_participant_details(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int
) -> Any:
    """Get detailed participant information including registration data"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get registration data if available
    from app.models.public_registration import PublicRegistration
    registration = db.query(PublicRegistration).filter(
        PublicRegistration.event_id == event_id,
        PublicRegistration.email == participant.email
    ).first()
    
    result = {
        "id": participant.id,
        "name": participant.full_name,
        "email": participant.email,
        "role": participant.role,
        "gender": None,
        "accommodation_needs": None
    }
    
    if registration:
        result["gender"] = registration.gender
        result["accommodation_needs"] = registration.accommodation_needs
    
    return result

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