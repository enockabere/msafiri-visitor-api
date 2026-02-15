"""Travel advance request models."""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Numeric, Enum
from sqlalchemy.orm import relationship

from app.db.database import Base


class ExpenseCategory(str, PyEnum):
    """Expense category for travel advances."""
    VISA_MONEY = "visa_money"
    PER_DIEM = "per_diem"
    SECURITY = "security"
    TICKET = "ticket"


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    expense_category = Column(Enum(ExpenseCategory), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(AdvanceStatus), default=AdvanceStatus.PENDING, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Approval tracking
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Disbursement tracking
    disbursed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    disbursed_at = Column(DateTime, nullable=True)
    disbursement_reference = Column(String(255), nullable=True)

    # Relationships
    travel_request = relationship("TravelRequest")
    traveler = relationship("TravelRequestTraveler")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    rejector = relationship("User", foreign_keys=[rejected_by])
    disburser = relationship("User", foreign_keys=[disbursed_by])
    tenant = relationship("Tenant")
