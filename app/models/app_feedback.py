from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
import enum

class FeedbackCategory(enum.Enum):
    USER_EXPERIENCE = "user_experience"
    PERFORMANCE = "performance"
    FEATURES = "features"
    BUG_REPORT = "bug_report"
    SUGGESTION = "suggestion"
    GENERAL = "general"

class AppFeedback(BaseModel):
    __tablename__ = "app_feedback"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    category = Column(Enum(FeedbackCategory), nullable=False)
    feedback_text = Column(Text, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])