from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/{event_id}/my-role", operation_id="get_my_event_role_unique")
def get_my_event_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's role in a specific event."""
    
    # Check if user is participant in this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a participant of this event"
        )
    
    # Get the participant role (facilitator, participant, etc.)
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    return {
        "event_id": event_id,
        "role": role or "participant",
        "status": participation.status,
        "is_facilitator": role == "facilitator"
    }