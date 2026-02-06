from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class EventBadge(Base):
    __tablename__ = "event_badges"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    badge_template_id = Column(Integer, ForeignKey("badge_templates.id"), nullable=False)
    template_variables = Column(JSON, nullable=False)  # Store template variable values
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="badges")
    badge_template = relationship("BadgeTemplate")
    tenant = relationship("Tenant")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<EventBadge(id={self.id}, event_id={self.event_id}, template_id={self.badge_template_id})>"


class ParticipantBadge(Base):
    __tablename__ = "participant_badges"

    id = Column(Integer, primary_key=True, index=True)
    event_badge_id = Column(Integer, ForeignKey("event_badges.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, index=True)
    badge_url = Column(String(500), nullable=True)  # Generated badge PDF URL
    badge_public_id = Column(String(255), nullable=True)  # Cloudinary public ID
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event_badge = relationship("EventBadge")
    participant = relationship("EventParticipant")

    def __repr__(self):
        return f"<ParticipantBadge(id={self.id}, participant_id={self.participant_id})>"
