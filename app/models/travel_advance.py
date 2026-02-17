"""Travel advance request models."""
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Integer, Numeric, Enum
from sqlalchemy.orm import relationship

from app.db.database import Base


class ExpenseCategory(str, PyEnum):
    """Expense category for travel advances."""
    PER_DIEM = "per_diem"


class AccommodationType(str, PyEnum):
    """Accommodation type for per diem advances."""
    FULL_BOARD = "full_board"
    HALF_BOARD = "half_board"
    BED_AND_BREAKFAST = "bed_and_breakfast"
    BED_ONLY = "bed_only"


class PaymentMethod(str, PyEnum):
    """Payment method for advances."""
    CASH = "cash"
    MPESA = "mpesa"
    BANK = "bank"


class CashHours(str, PyEnum):
    """Cash pickup hours."""
    MORNING = "morning"  # 10:00 AM - 12:30 PM
    AFTERNOON = "afternoon"  # 2:00 PM - 3:30 PM


class AdvanceStatus(str, PyEnum):
    """Status of travel advance request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"


class TravelAdvance(Base):
    """Travel advance request model."""
    __tablename__ = "travel_advances"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    traveler_id = Column(Integer, ForeignKey("travel_request_travelers.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    expense_category = Column(Enum(ExpenseCategory), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES")
    status = Column(Enum(AdvanceStatus), default=AdvanceStatus.PENDING, nullable=False, index=True)

    # Per diem specific - accommodation type
    accommodation_type = Column(Enum(AccommodationType), nullable=True)

    # Payment details
    payment_method = Column(Enum(PaymentMethod), nullable=False, default=PaymentMethod.CASH)
    cash_pickup_date = Column(Date, nullable=True)
    cash_hours = Column(Enum(CashHours), nullable=True)
    mpesa_number = Column(String(20), nullable=True)
    bank_account = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest")
    traveler = relationship("TravelRequestTraveler")
    tenant = relationship("Tenant")
