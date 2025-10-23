from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class ParticipantRole(enum.Enum):
    ATTENDEE = "attendee"
    SPEAKER = "speaker"
    ORGANIZER = "organizer"
    VIP = "vip"

class ParticipantStatus(enum.Enum):
    REGISTERED = "registered"  # User self-registered
    SELECTED = "selected"     # Admin selected for event
    NOT_SELECTED = "not_selected"  # Admin rejected
    WAITING = "waiting"       # On waiting list
    CANCELED = "canceled"     # Registration canceled
    ATTENDED = "attended"     # Actually attended

class EventParticipant(BaseModel):
    __tablename__ = "event_participants"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Link to user account
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default='attendee')
    participant_role = Column(String(50), default='visitor')  # Event-specific role: visitor, facilitator, organizer
    status = Column(String(50), default='registered')  # Default to registered
    # registration_type = Column(String(50), default='self')  # 'self' or 'admin'
    invited_by = Column(String(255), nullable=False)  # Keep original column name for now
    # notes = Column(Text, nullable=True)  # Admin notes
    
    # Registration details
    country = Column(String(100), nullable=True)
    position = Column(String(255), nullable=True)
    project = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    eta = Column(String(255), nullable=True)  # Expected Time of Arrival
    requires_eta = Column(Boolean, default=False)
    
    # Document upload tracking
    passport_document = Column(String(500), nullable=True)
    ticket_document = Column(String(500), nullable=True)
    
    # Registration form fields
    dietary_requirements = Column(Text, nullable=True)
    accommodation_type = Column(String(100), nullable=True)
    participant_name = Column(String(255), nullable=True)
    participant_email = Column(String(255), nullable=True)
    
    # Invitation tracking fields (will be added to DB later)
    # invitation_sent = Column(Boolean, default=False)
    # invitation_sent_at = Column(DateTime, nullable=True)
    # invitation_accepted = Column(Boolean, default=False)
    # invitation_accepted_at = Column(DateTime, nullable=True)
    
    # Decline tracking fields
    decline_reason = Column(Text, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    # user = relationship("User", foreign_keys=[user_id])