from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PerdiemStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"

class PerdiemRequest(BaseModel):
    __tablename__ = "perdiem_requests"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    arrival_date = Column(Date, nullable=False)
    departure_date = Column(Date, nullable=False)
    calculated_days = Column(Integer, nullable=False)  # Auto-calculated from events
    requested_days = Column(Integer, nullable=False)   # User can adjust
    daily_rate = Column(Numeric(10,2), nullable=False)
    total_amount = Column(Numeric(10,2), nullable=False)
    status = Column(Enum(PerdiemStatus), default=PerdiemStatus.PENDING)
    justification = Column(Text)  # Why user adjusted days
    admin_notes = Column(Text)
    approved_by = Column(String(255))
    payment_reference = Column(String(255))
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="perdiem_requests")