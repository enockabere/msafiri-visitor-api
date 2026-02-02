from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Boolean, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PerdiemStatus(enum.Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ISSUED = "issued"
    COMPLETED = "completed"

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
    status = Column(String(50), default="open")
    justification = Column(Text)  # Why user adjusted days
    event_type = Column(String(100))  # Event type (Meeting, Training, etc.)
    purpose = Column(Text)  # Purpose/justification for the per diem
    approver_title = Column(String(50))  # FinCo or Travel Admin
    approver_email = Column(String(255))  # Approver's email
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
    approved_by = Column(String(255))  # Approver email
    approved_at = Column(DateTime)
    rejected_by = Column(String(255))
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    
    payment_reference = Column(String(255))
    currency = Column(String(10), default="USD")  # Currency for the per diem payment
    
    # Approval details
    approver_role = Column(String(100))  # FinCo or Travel Admin
    approver_full_name = Column(String(255))  # Full name of approver
    budget_code = Column(String(100))  # Budget code
    activity_code = Column(String(100))  # Activity code
    cost_center = Column(String(100))  # Cost center
    section = Column(String(50))  # OCA, OCB, OCBA, OCG, WACA

    # Accommodation details (from user's active accommodation for the event)
    accommodation_type = Column(String(50))  # FullBoard, HalfBoard, BedAndBreakfast, BedOnly
    accommodation_name = Column(String(255))  # Hotel/Guesthouse name

    # Accommodation deduction breakdown (calculated at approval time)
    accommodation_days = Column(Integer)  # Number of days with accommodation
    accommodation_rate = Column(Numeric(10,2))  # Rate applied for accommodation type
    accommodation_deduction = Column(Numeric(10,2))  # Total deduction: accommodation_rate * accommodation_days
    per_diem_base_amount = Column(Numeric(10,2))  # Base amount: daily_rate * requested_days

    # Relationships
    participant = relationship("EventParticipant", back_populates="perdiem_requests")