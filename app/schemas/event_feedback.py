# File: app/schemas/event_feedback.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class EventFeedbackBase(BaseModel):
    participant_email: str
    participant_name: str
    overall_rating: float
    content_rating: Optional[float] = None
    organization_rating: Optional[float] = None
    venue_rating: Optional[float] = None
    feedback_text: Optional[str] = None
    suggestions: Optional[str] = None
    would_recommend: Optional[str] = None

class EventFeedbackCreate(EventFeedbackBase):
    event_id: int

class EventFeedback(EventFeedbackBase):
    id: int
    event_id: int
    participant_id: Optional[int] = None
    submitted_at: datetime
    ip_address: Optional[str] = None
    
    class Config:
        from_attributes = True

class EventFeedbackStats(BaseModel):
    total_responses: int
    average_overall_rating: float
    average_content_rating: Optional[float] = None
    average_organization_rating: Optional[float] = None
    average_venue_rating: Optional[float] = None
    recommendation_percentage: Optional[float] = None
