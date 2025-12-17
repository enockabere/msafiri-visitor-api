# File: app/api/v1/endpoints/participant_response.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant, DeclineReason

router = APIRouter()

class ParticipantResponseRequest(BaseModel):
    event_id: int
    response: str  # "confirm" or "decline"
    decline_reason: Optional[DeclineReason] = None

class DeclineReasonsResponse(BaseModel):
    reasons: list[str]

@router.get("/decline-reasons", response_model=DeclineReasonsResponse)
def get_decline_reasons():
    """Get list of available decline reasons"""
    reasons = [reason.value for reason in DeclineReason]
    return DeclineReasonsResponse(reasons=reasons)

@router.post("/respond")
def respond_to_event_invitation(
    response_data: ParticipantResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm or decline event participation"""
    
    # Find participant record
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == response_data.event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant record not found"
        )
    
    # Check if participant is selected
    if participant.status != "selected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only selected participants can respond"
        )
    
    # Process response
    if response_data.response == "confirm":
        participant.status = "confirmed"
        participant.confirmed_at = datetime.utcnow()
        participant.decline_reason = None
        participant.declined_at = None
        
    elif response_data.response == "decline":
        if not response_data.decline_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decline reason is required"
            )
        
        participant.status = "declined"
        participant.decline_reason = response_data.decline_reason
        participant.declined_at = datetime.utcnow()
        participant.confirmed_at = None
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response must be 'confirm' or 'decline'"
        )
    
    db.commit()
    db.refresh(participant)
    
    return {
        "message": f"Successfully {response_data.response}ed participation",
        "status": participant.status,
        "decline_reason": participant.decline_reason.value if participant.decline_reason else None
    }

@router.get("/my-events")
def get_my_selected_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get events where user is selected and can respond"""
    
    participants = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(["selected", "confirmed", "declined"])
    ).all()
    
    result = []
    for participant in participants:
        result.append({
            "event_id": participant.event_id,
            "event": participant.event,
            "status": participant.status,
            "decline_reason": participant.decline_reason.value if participant.decline_reason else None,
            "confirmed_at": participant.confirmed_at,
            "declined_at": participant.declined_at
        })
    
    return result