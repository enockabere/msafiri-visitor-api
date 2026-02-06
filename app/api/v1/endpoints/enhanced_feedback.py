from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from pydantic import BaseModel

router = APIRouter()

class EventFeedbackCreate(BaseModel):
    participant_email: str
    participant_name: str
    overall_rating: int
    accommodation_rating: Optional[int] = None
    transport_rating: Optional[int] = None
    food_rating: Optional[int] = None
    venue_rating: Optional[int] = None
    organization_rating: Optional[int] = None
    content_rating: Optional[int] = None
    feedback_text: Optional[str] = None
    suggestions: Optional[str] = None
    would_recommend: Optional[bool] = None

class SessionFeedbackCreate(BaseModel):
    agenda_item_id: int
    participant_email: str
    participant_name: str
    session_rating: int
    content_rating: Optional[int] = None
    feedback_text: Optional[str] = None
    suggestions: Optional[str] = None

@router.post("/event", response_model=dict)
def create_event_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    feedback_in: EventFeedbackCreate
) -> Any:
    """Create event-level feedback"""
    
    # Check if feedback already exists
    existing = db.execute(
        text("SELECT id FROM event_feedback WHERE event_id = :event_id AND participant_email = :email AND feedback_type = 'event'"),
        {"event_id": event_id, "email": feedback_in.participant_email}
    ).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Event feedback already submitted")
    
    # Create feedback
    db.execute(
        text("""
            INSERT INTO event_feedback (
                event_id, participant_email, participant_name, feedback_type,
                overall_rating, accommodation_rating, transport_rating, food_rating,
                venue_rating, organization_rating, content_rating,
                feedback_text, suggestions, would_recommend
            ) VALUES (
                :event_id, :email, :name, 'event',
                :overall_rating, :accommodation_rating, :transport_rating, :food_rating,
                :venue_rating, :organization_rating, :content_rating,
                :feedback_text, :suggestions, :would_recommend
            )
        """),
        {
            "event_id": event_id,
            "email": feedback_in.participant_email,
            "name": feedback_in.participant_name,
            "overall_rating": feedback_in.overall_rating,
            "accommodation_rating": feedback_in.accommodation_rating,
            "transport_rating": feedback_in.transport_rating,
            "food_rating": feedback_in.food_rating,
            "venue_rating": feedback_in.venue_rating,
            "organization_rating": feedback_in.organization_rating,
            "content_rating": feedback_in.content_rating,
            "feedback_text": feedback_in.feedback_text,
            "suggestions": feedback_in.suggestions,
            "would_recommend": feedback_in.would_recommend
        }
    )
    db.commit()
    
    return {"message": "Event feedback submitted successfully"}

@router.post("/session", response_model=dict)
def create_session_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    feedback_in: SessionFeedbackCreate
) -> Any:
    """Create session-level feedback"""
    
    # Check if feedback already exists
    existing = db.execute(
        text("SELECT id FROM event_feedback WHERE event_id = :event_id AND agenda_item_id = :agenda_id AND participant_email = :email AND feedback_type = 'session'"),
        {"event_id": event_id, "agenda_id": feedback_in.agenda_item_id, "email": feedback_in.participant_email}
    ).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Session feedback already submitted")
    
    # Create feedback
    db.execute(
        text("""
            INSERT INTO event_feedback (
                event_id, agenda_item_id, participant_email, participant_name, feedback_type,
                session_rating, content_rating, feedback_text, suggestions
            ) VALUES (
                :event_id, :agenda_id, :email, :name, 'session',
                :session_rating, :content_rating, :feedback_text, :suggestions
            )
        """),
        {
            "event_id": event_id,
            "agenda_id": feedback_in.agenda_item_id,
            "email": feedback_in.participant_email,
            "name": feedback_in.participant_name,
            "session_rating": feedback_in.session_rating,
            "content_rating": feedback_in.content_rating,
            "feedback_text": feedback_in.feedback_text,
            "suggestions": feedback_in.suggestions
        }
    )
    db.commit()
    
    return {"message": "Session feedback submitted successfully"}

@router.get("/event", response_model=List[dict])
def get_event_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get event-level feedback"""
    
    result = db.execute(
        text("""
            SELECT participant_name, participant_email, overall_rating,
                   accommodation_rating, transport_rating, food_rating,
                   venue_rating, organization_rating, content_rating,
                   feedback_text, suggestions, would_recommend, submitted_at
            FROM event_feedback 
            WHERE event_id = :event_id AND feedback_type = 'event'
            ORDER BY submitted_at DESC
        """),
        {"event_id": event_id}
    ).fetchall()
    
    return [
        {
            "participant_name": row[0],
            "participant_email": row[1],
            "overall_rating": row[2],
            "accommodation_rating": row[3],
            "transport_rating": row[4],
            "food_rating": row[5],
            "venue_rating": row[6],
            "organization_rating": row[7],
            "content_rating": row[8],
            "feedback_text": row[9],
            "suggestions": row[10],
            "would_recommend": row[11],
            "submitted_at": row[12].isoformat() if row[12] else None
        }
        for row in result
    ]

@router.get("/session/{agenda_item_id}", response_model=List[dict])
def get_session_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_item_id: int
) -> Any:
    """Get session-level feedback"""
    
    result = db.execute(
        text("""
            SELECT f.participant_name, f.participant_email, f.session_rating,
                   f.content_rating, f.feedback_text, f.suggestions, f.submitted_at,
                   a.title as session_title
            FROM event_feedback f
            JOIN event_agenda a ON f.agenda_item_id = a.id
            WHERE f.event_id = :event_id AND f.agenda_item_id = :agenda_id AND f.feedback_type = 'session'
            ORDER BY f.submitted_at DESC
        """),
        {"event_id": event_id, "agenda_id": agenda_item_id}
    ).fetchall()
    
    return [
        {
            "participant_name": row[0],
            "participant_email": row[1],
            "session_rating": row[2],
            "content_rating": row[3],
            "feedback_text": row[4],
            "suggestions": row[5],
            "submitted_at": row[6].isoformat() if row[6] else None,
            "session_title": row[7]
        }
        for row in result
    ]

@router.get("/stats", response_model=dict)
def get_feedback_stats(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get feedback statistics"""
    
    # Event feedback stats
    event_stats = db.execute(
        text("""
            SELECT 
                COUNT(*) as total_responses,
                AVG(overall_rating) as avg_overall_rating,
                AVG(accommodation_rating) as avg_accommodation_rating,
                AVG(transport_rating) as avg_transport_rating,
                AVG(food_rating) as avg_food_rating,
                AVG(venue_rating) as avg_venue_rating,
                AVG(organization_rating) as avg_organization_rating,
                AVG(content_rating) as avg_content_rating,
                COUNT(CASE WHEN would_recommend = true THEN 1 END) * 100.0 / COUNT(*) as recommendation_percentage
            FROM event_feedback 
            WHERE event_id = :event_id AND feedback_type = 'event'
        """),
        {"event_id": event_id}
    ).fetchone()
    
    # Session feedback stats
    session_stats = db.execute(
        text("""
            SELECT 
                a.title,
                COUNT(f.id) as response_count,
                AVG(f.session_rating) as avg_session_rating,
                AVG(f.content_rating) as avg_content_rating
            FROM event_agenda a
            LEFT JOIN event_feedback f ON a.id = f.agenda_item_id AND f.feedback_type = 'session'
            WHERE a.event_id = :event_id
            GROUP BY a.id, a.title
            ORDER BY a.start_datetime
        """),
        {"event_id": event_id}
    ).fetchall()
    
    return {
        "event_feedback": {
            "total_responses": event_stats[0] if event_stats else 0,
            "average_overall_rating": round(event_stats[1], 2) if event_stats and event_stats[1] else 0,
            "average_accommodation_rating": round(event_stats[2], 2) if event_stats and event_stats[2] else 0,
            "average_transport_rating": round(event_stats[3], 2) if event_stats and event_stats[3] else 0,
            "average_food_rating": round(event_stats[4], 2) if event_stats and event_stats[4] else 0,
            "average_venue_rating": round(event_stats[5], 2) if event_stats and event_stats[5] else 0,
            "average_organization_rating": round(event_stats[6], 2) if event_stats and event_stats[6] else 0,
            "average_content_rating": round(event_stats[7], 2) if event_stats and event_stats[7] else 0,
            "recommendation_percentage": round(event_stats[8], 1) if event_stats and event_stats[8] else 0
        },
        "session_feedback": [
            {
                "session_title": row[0],
                "response_count": row[1],
                "average_session_rating": round(row[2], 2) if row[2] else 0,
                "average_content_rating": round(row[3], 2) if row[3] else 0
            }
            for row in session_stats
        ]
    }
