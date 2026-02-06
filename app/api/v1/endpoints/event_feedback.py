# File: app/api/v1/endpoints/event_feedback.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.event_feedback import EventFeedback
from app.models.event import Event
from app.schemas.event_feedback import EventFeedbackCreate, EventFeedback as EventFeedbackSchema, EventFeedbackStats
from app.models.user import User

router = APIRouter()

@router.post("/{event_id}/feedback", response_model=EventFeedbackSchema)
def submit_event_feedback(
    event_id: int,
    feedback_data: EventFeedbackCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit feedback for an event"""
    
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if feedback already exists for this email
    existing = db.query(EventFeedback).filter(
        and_(
            EventFeedback.event_id == event_id,
            EventFeedback.participant_email == feedback_data.participant_email
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this event")
    
    # Create feedback
    feedback = EventFeedback(
        event_id=event_id,
        participant_email=feedback_data.participant_email,
        participant_name=feedback_data.participant_name,
        overall_rating=feedback_data.overall_rating,
        content_rating=feedback_data.content_rating,
        organization_rating=feedback_data.organization_rating,
        venue_rating=feedback_data.venue_rating,
        feedback_text=feedback_data.feedback_text,
        suggestions=feedback_data.suggestions,
        would_recommend=feedback_data.would_recommend,
        ip_address=request.client.host,
        submitted_at=func.now()
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback

@router.get("/{event_id}/feedback", response_model=List[EventFeedbackSchema])
def get_event_feedback(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get all feedback for an event (admin only)"""
    
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    feedback = db.query(EventFeedback).filter(EventFeedback.event_id == event_id).all()
    return feedback

@router.get("/{event_id}/feedback/stats", response_model=EventFeedbackStats)
def get_event_feedback_stats(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get feedback statistics for an event"""
    
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get statistics
    stats = db.query(
        func.count(EventFeedback.id).label('total_responses'),
        func.avg(EventFeedback.overall_rating).label('avg_overall'),
        func.avg(EventFeedback.content_rating).label('avg_content'),
        func.avg(EventFeedback.organization_rating).label('avg_organization'),
        func.avg(EventFeedback.venue_rating).label('avg_venue')
    ).filter(EventFeedback.event_id == event_id).first()
    
    # Calculate recommendation percentage
    recommend_count = db.query(func.count(EventFeedback.id)).filter(
        and_(
            EventFeedback.event_id == event_id,
            EventFeedback.would_recommend == "Yes"
        )
    ).scalar()
    
    total_responses = stats.total_responses or 0
    recommendation_percentage = (recommend_count / total_responses * 100) if total_responses > 0 else None
    
    return EventFeedbackStats(
        total_responses=total_responses,
        average_overall_rating=round(stats.avg_overall, 2) if stats.avg_overall else 0.0,
        average_content_rating=round(stats.avg_content, 2) if stats.avg_content else None,
        average_organization_rating=round(stats.avg_organization, 2) if stats.avg_organization else None,
        average_venue_rating=round(stats.avg_venue, 2) if stats.avg_venue else None,
        recommendation_percentage=round(recommendation_percentage, 1) if recommendation_percentage else None
    )
