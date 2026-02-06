from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ParticipantVoucherRedemption(BaseModel):
    __tablename__ = "participant_voucher_redemptions"
    
    allocation_id = Column(Integer, ForeignKey("event_allocations.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    redeemed_at = Column(DateTime, nullable=False)
    redeemed_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    allocation = relationship("EventAllocation")
    participant = relationship("EventParticipant")
