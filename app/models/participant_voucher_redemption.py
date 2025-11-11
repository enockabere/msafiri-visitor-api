from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ParticipantVoucherRedemption(BaseModel):
    __tablename__ = "participant_voucher_redemptions"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Direct user reference
    redeemed_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Scanner user ID
    redeemed_at = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=True)  # Where voucher was redeemed
    notes = Column(Text, nullable=True)
    
    # Relationships
    event = relationship("Event")
    participant = relationship("User", foreign_keys=[participant_id])
    scanner = relationship("User", foreign_keys=[redeemed_by])