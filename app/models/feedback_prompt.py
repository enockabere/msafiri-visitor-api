from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class FeedbackPrompt(BaseModel):
    __tablename__ = "feedback_prompts"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_prompted_at = Column(DateTime(timezone=True), nullable=True)
    prompt_count = Column(Integer, default=0)
    dismissed_count = Column(Integer, default=0)
    has_submitted_feedback = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
