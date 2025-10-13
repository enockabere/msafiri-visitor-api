from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class BriefType(enum.Enum):
    GENERAL = "general"
    EVENT_SPECIFIC = "event_specific"

class ContentType(enum.Enum):
    TEXT = "text"
    VIDEO = "video"

class SecurityBrief(BaseModel):
    __tablename__ = "security_briefs"
    
    title = Column(String(255), nullable=False)
    brief_type = Column(Enum(BriefType), nullable=False)
    content_type = Column(Enum(ContentType), nullable=False)
    content = Column(Text, nullable=False)  # Text content or video URL
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Only for event-specific briefs
    status = Column(String(50), default="draft")
    publish_start_date = Column(String(255), nullable=True)
    publish_end_date = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), nullable=False)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")

class UserBriefAcknowledgment(BaseModel):
    __tablename__ = "user_brief_acknowledgments"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    brief_id = Column(Integer, ForeignKey("security_briefs.id"), nullable=False)
    acknowledged_at = Column(String(255), nullable=False)  # User email who acknowledged
    
    # Relationships
    brief = relationship("SecurityBrief")