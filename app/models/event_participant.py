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
    status = Column(String(50), default='registered')  # Default to registered
    # registration_type = Column(String(50), default='self')  # 'self' or 'admin'
    invited_by = Column(String(255), nullable=False)  # Keep original column name for now
    # notes = Column(Text, nullable=True)  # Admin notes
    
    # Invitation tracking fields (will be added to DB later)
    # invitation_sent = Column(Boolean, default=False)
    # invitation_sent_at = Column(DateTime, nullable=True)
    # invitation_accepted = Column(Boolean, default=False)
    # invitation_accepted_at = Column(DateTime, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    # user = relationship("User", foreign_keys=[user_id])