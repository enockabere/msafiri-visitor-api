from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class ParticipantVoucherRedemption(Base):
    __tablename__ = "participant_voucher_redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("event_allocations.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    redeemed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    allocation = relationship("EventAllocation")
    participant = relationship("EventParticipant")