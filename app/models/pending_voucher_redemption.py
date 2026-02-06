from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class PendingVoucherRedemption(BaseModel):
    __tablename__ = "pending_voucher_redemptions"
    
    token = Column(String(255), unique=True, nullable=False, index=True)
    allocation_id = Column(Integer, ForeignKey("event_allocations.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, completed, expired, cancelled
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(255), nullable=True)
    
    # Relationships
    allocation = relationship("EventAllocation")
    participant = relationship("EventParticipant")
