from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from sqlalchemy import text

router = APIRouter()

@router.get("/{event_id}/agenda")
def get_event_agenda(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get event agenda items."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🗓️ Get agenda - Event: {event_id}, User: {current_user.email}")
    
    # Check if user has access to this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(['selected', 'approved', 'confirmed', 'checked_in'])
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    # Mock agenda data for now
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    agenda_items = [
        {
            "id": 1,
            "title": "Welcome & Registration",
            "description": "Check-in and welcome coffee",
            "start_time": "09:00",
            "end_time": "09:30",
            "start_datetime": f"{today}T09:00:00",
            "end_datetime": f"{today}T09:30:00",
            "event_id": event_id,
            "presenter": "Event Team"
        },
        {
            "id": 2,
            "title": "Opening Session",
            "description": "Introduction and overview of the event",
            "start_time": "09:30",
            "end_time": "10:30",
            "start_datetime": f"{today}T09:30:00",
            "end_datetime": f"{today}T10:30:00",
            "event_id": event_id,
            "presenter": "Dr. John Smith"
        },
        {
            "id": 3,
            "title": "Coffee Break",
            "description": "Networking and refreshments",
            "start_time": "10:30",
            "end_time": "11:00",
            "start_datetime": f"{today}T10:30:00",
            "end_datetime": f"{today}T11:00:00",
            "event_id": event_id,
            "presenter": ""
        },
        {
            "id": 4,
            "title": "Technical Session",
            "description": "Deep dive into technical topics",
            "start_time": "11:00",
            "end_time": "12:30",
            "start_datetime": f"{today}T11:00:00",
            "end_datetime": f"{today}T12:30:00",
            "event_id": event_id,
            "presenter": "Jane Doe"
        },
        {
            "id": 5,
            "title": "Lunch Break",
            "description": "Networking lunch",
            "start_time": "12:30",
            "end_time": "13:30",
            "start_datetime": f"{today}T12:30:00",
            "end_datetime": f"{today}T13:30:00",
            "event_id": event_id,
            "presenter": ""
        }
    ]
    
    logger.info(f"📊 Found {len(agenda_items)} agenda items")
    return agenda_items

@router.get("/{event_id}/my-role")
def get_my_event_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's role in the event."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"👤 Get user role - Event: {event_id}, User: {current_user.email}")
    
    # Check participation and role
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a participant of this event"
        )
    
    # Check both role and participant_role fields
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    logger.info(f"📊 User role: {role}")
    return {"role": role}

@router.post("/{event_id}/agenda")
def create_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create new agenda item (facilitators only)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"➕ Create agenda item - Event: {event_id}, User: {current_user.email}")
    
    # Check if user is a facilitator
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    # Check if user is facilitator
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role != 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - only facilitators can manage agenda"
        )
    
    logger.info(f"✅ Agenda item created successfully")
    return {"message": "Agenda item created successfully", "id": 999}

@router.put("/{event_id}/agenda/{agenda_id}")
def update_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    agenda_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update agenda item (facilitators only)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"✏️ Update agenda item - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if user is a facilitator (same logic as create)
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role != 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - only facilitators can manage agenda"
        )
    
    logger.info(f"✅ Agenda item updated successfully")
    return {"message": "Agenda item updated successfully"}

@router.delete("/{event_id}/agenda/{agenda_id}")
def delete_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Delete agenda item (facilitators only)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🗑️ Delete agenda item - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if user is a facilitator (same logic as create)
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role != 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - only facilitators can manage agenda"
        )
    
    logger.info(f"✅ Agenda item deleted successfully")
    return {"message": "Agenda item deleted successfully"}

@router.post("/{event_id}/agenda/{agenda_id}/feedback")
def submit_agenda_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    feedback_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Submit feedback for an agenda item."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"💬 Submit agenda feedback - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if user has access to this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(['selected', 'approved', 'confirmed', 'checked_in'])
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    # Check if agenda item exists
    valid_agenda_ids = [1, 2, 3, 4, 5]  # Match the mock agenda items
    if agenda_id not in valid_agenda_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agenda item {agenda_id} not found"
        )
    
    # Check if user is not a facilitator (facilitators shouldn't give feedback)
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role == 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Facilitators cannot submit feedback"
        )
    
    # Mock feedback submission - in real implementation, save to database
    logger.info(f"📊 Feedback: Rating={feedback_data.get('rating')}, Comment={feedback_data.get('comment')}")
    logger.info(f"✅ Agenda feedback submitted successfully")
    
    return {"message": "Feedback submitted successfully"}