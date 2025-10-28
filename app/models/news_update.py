from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.models.base import Base

class NewsCategory(str, enum.Enum):
    HEALTH_PROGRAM = "health_program"
    SECURITY_BRIEFING = "security_briefing"
    EVENTS = "events"
    REPORTS = "reports"
    GENERAL = "general"
    ANNOUNCEMENT = "announcement"

class NewsUpdate(Base):
    __tablename__ = "news_updates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    external_link = Column(String(500), nullable=True)  # External link instead of full content
    video_url = Column(String(500), nullable=True)  # Video URL
    document_url = Column(String(500), nullable=True)  # Document URL
    content_type = Column(String(20), default="text")  # "text" or "link"
    category = Column(Enum(NewsCategory), nullable=False, default=NewsCategory.GENERAL)
    is_important = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    scheduled_publish_at = Column(DateTime(timezone=True), nullable=True)  # For scheduled publishing
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When to hide from mobile
    image_url = Column(String(500), nullable=True)
    created_by = Column(String(255), nullable=False)  # Email of creator
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="news_updates")