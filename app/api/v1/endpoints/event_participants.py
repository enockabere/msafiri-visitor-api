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
    
    query = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    )
    
    if role:
        query = query.filter(EventParticipant.role == role)
    
    participants = query.offset(skip).limit(limit).all()
    return participants

@router.put("/{participant_id}/role", response_model=schemas.event_participant.EventParticipant)
def update_participant_role(
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
    
    # Update participant_role (event-specific role)
    participant.participant_role = new_role
    db.commit()
    db.refresh(participant)
    
    return participant

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