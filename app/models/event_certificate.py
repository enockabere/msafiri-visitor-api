from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime

class EventCertificate(Base):
    __tablename__ = "event_certificates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    certificate_template_id = Column(Integer, ForeignKey("certificate_templates.id"), nullable=False)
    template_variables = Column(JSON, nullable=False)  # Store template variable values
    certificate_date = Column(DateTime, nullable=True)  # Date when certificate becomes available
    is_published = Column(Boolean, default=False, nullable=False)  # Controls visibility to participants
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="certificates")
    certificate_template = relationship("CertificateTemplate")
    tenant = relationship("Tenant")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<EventCertificate(id={self.id}, event_id={self.event_id}, template_id={self.certificate_template_id})>"


class ParticipantCertificate(Base):
    __tablename__ = "participant_certificates"

    id = Column(Integer, primary_key=True, index=True)
    event_certificate_id = Column(Integer, ForeignKey("event_certificates.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, index=True)
    certificate_url = Column(String(500), nullable=True)  # Generated certificate PDF URL
    certificate_public_id = Column(String(255), nullable=True)  # Cloudinary public ID
    email_sent = Column(Boolean, default=False, nullable=False)  # Track if email notification was sent
    email_sent_at = Column(DateTime, nullable=True)  # When email was sent
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event_certificate = relationship("EventCertificate")
    participant = relationship("EventParticipant")

    def __repr__(self):
        return f"<ParticipantCertificate(id={self.id}, participant_id={self.participant_id})>"