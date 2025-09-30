from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ParticipantPerdiem(BaseModel):
    __tablename__ = "participant_perdiem"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    daily_rate = Column(Numeric(10,2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10,2), nullable=False)
    approved = Column(Boolean, default=False)
    paid = Column(Boolean, default=False)
    approved_by = Column(String(255))
    payment_reference = Column(String(255))
    notes = Column(String(500))
    
    # Relationships
    participant = relationship("EventParticipant")
    event = relationship("Event")

class EventConflictCheck(BaseModel):
    __tablename__ = "event_conflict_checks"
    
    participant_email = Column(String(255), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    conflicting_event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    conflict_type = Column(String(50), nullable=False)  # "overlap", "same_day"
    resolved = Column(Boolean, default=False)
    
    # Relationships
    event = relationship("Event", foreign_keys=[event_id])
    conflicting_event = relationship("Event", foreign_keys=[conflicting_event_id])