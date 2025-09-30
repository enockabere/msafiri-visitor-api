# File: app/models/event_feedback.py
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class EventFeedback(BaseModel):
    __tablename__ = "event_feedback"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=True, index=True)
    participant_email = Column(String(255), nullable=False, index=True)
    participant_name = Column(String(255), nullable=False)
    
    # Ratings (1-5 scale)
    overall_rating = Column(Float, nullable=False)
    content_rating = Column(Float, nullable=True)
    organization_rating = Column(Float, nullable=True)
    venue_rating = Column(Float, nullable=True)
    
    # Feedback text
    feedback_text = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    
    # Would recommend
    would_recommend = Column(String(10), nullable=True)  # "Yes", "No", "Maybe"
    
    # Tracking
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    event = relationship("Event")