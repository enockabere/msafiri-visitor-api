from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class AgendaFeedback(Base):
    __tablename__ = "agenda_feedback"

    id = Column(Integer, primary_key=True, index=True)
    agenda_id = Column(Integer, ForeignKey("event_agenda.id"), nullable=False)
    user_email = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = relationship("FeedbackResponse", back_populates="feedback", cascade="all, delete-orphan")

class FeedbackResponse(Base):
    __tablename__ = "feedback_responses"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("agenda_feedback.id"), nullable=False)
    responder_email = Column(String, nullable=False)
    response_text = Column(Text, nullable=False)
    is_like = Column(Boolean, default=False)  # True for like, False for comment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    feedback = relationship("AgendaFeedback", back_populates="responses")