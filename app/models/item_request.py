from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"

class ItemRequest(BaseModel):
    __tablename__ = "item_requests"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    allocation_id = Column(Integer, ForeignKey("participant_allocations.id"), nullable=False)
    requested_quantity = Column(Integer, nullable=False, default=1)
    status = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    notes = Column(String(500))
    approved_by = Column(String(255))
    
    # Relationships
    participant = relationship("EventParticipant")
    allocation = relationship("ParticipantAllocation")
