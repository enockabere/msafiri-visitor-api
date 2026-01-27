from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Boolean, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PerdiemStatus(enum.Enum):
    PENDING = "pending"
    LINE_MANAGER_APPROVED = "line_manager_approved"
    BUDGET_OWNER_APPROVED = "budget_owner_approved"
    REJECTED = "rejected"
    PAID = "paid"

class PaymentMethod(enum.Enum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"

class CashHours(enum.Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"

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
    event_type = Column(String(100))  # Event type (Meeting, Training, etc.)
    admin_notes = Column(Text)
    
    # Contact details
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Payment method
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    
    # Cash payment details
    cash_pickup_date = Column(Date)
    cash_hours = Column(Enum(CashHours))
    
    # Mobile money details
    mpesa_number = Column(String(20))
    
    # Approval workflow
    line_manager_approved_by = Column(String(255))
    line_manager_approved_at = Column(DateTime)
    budget_owner_approved_by = Column(String(255))
    budget_owner_approved_at = Column(DateTime)
    rejected_by = Column(String(255))
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    payment_reference = Column(String(255))
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="perdiem_requests")