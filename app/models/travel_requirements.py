from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class EventTravelRequirement(BaseModel):
    __tablename__ = "event_travel_requirements"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    requirement_type = Column(String(50), nullable=False)  # 'eta', 'health', etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    deadline_days_before = Column(Integer)  # Days before travel
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")

class ParticipantRequirementStatus(BaseModel):
    __tablename__ = "participant_requirement_status"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("event_travel_requirements.id"), nullable=False)
    completed = Column(Boolean, default=False)
    completion_notes = Column(Text)
    completed_by = Column(String(255))
    
    # Relationships
    participant = relationship("EventParticipant")
    requirement = relationship("EventTravelRequirement")
