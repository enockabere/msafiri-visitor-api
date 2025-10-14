from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/{event_id}/agenda/{agenda_id}/feedback")
def get_agenda_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get feedback for an agenda item."""
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    from app.models.agenda_feedback import AgendaFeedback, FeedbackResponse
    
    # Check user role
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role == 'facilitator':
        # Facilitators can see all feedback for their agenda items
        feedback_list = db.query(AgendaFeedback).filter(
            AgendaFeedback.agenda_id == agenda_id
        ).all()
    else:
        # Regular participants can only see their own feedback
        feedback_list = db.query(AgendaFeedback).filter(
            AgendaFeedback.agenda_id == agenda_id,
            AgendaFeedback.user_email == current_user.email
        ).all()
    
    # Format response with responses
    result = []
    for feedback in feedback_list:
        responses = db.query(FeedbackResponse).filter(
            FeedbackResponse.feedback_id == feedback.id
        ).all()
        
        result.append({
            "id": feedback.id,
            "user_email": feedback.user_email,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "created_at": feedback.created_at.isoformat(),
            "responses": [{
                "id": resp.id,
                "responder_email": resp.responder_email,
                "response_text": resp.response_text,
                "is_like": resp.is_like,
                "created_at": resp.created_at.isoformat()
            } for resp in responses]
        })
    
    return result

@router.post("/{event_id}/agenda/{agenda_id}/feedback/{feedback_id}/respond")
def respond_to_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    feedback_id: int,
    response_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Respond to feedback (facilitators only)."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if user is facilitator
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
            detail="Only facilitators can respond to feedback"
        )
    
    # Check if feedback exists
    from app.models.agenda_feedback import AgendaFeedback, FeedbackResponse
    
    feedback = db.query(AgendaFeedback).filter(
        AgendaFeedback.id == feedback_id,
        AgendaFeedback.agenda_id == agenda_id
    ).first()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Create response
    response = FeedbackResponse(
        feedback_id=feedback_id,
        responder_email=current_user.email,
        response_text=response_data.get('response_text', ''),
        is_like=response_data.get('is_like', False)
    )
    
    db.add(response)
    db.commit()
    db.refresh(response)
    
    # TODO: Send push notification to feedback author
    logger.info(f"📱 Should send notification to {feedback.user_email}")
    
    return {"message": "Response submitted successfully", "response_id": response.id}