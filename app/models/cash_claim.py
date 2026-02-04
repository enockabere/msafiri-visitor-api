from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="draft")
    total_amount = Column(Numeric(10, 2), default=0.0)
    description = Column(Text)
    expense_type = Column(String(50))  # MEDICAL, OPERATIONAL, TRAVEL
    payment_method = Column(String(50))  # CASH, BANK, MPESA
    cash_pickup_date = Column(DateTime(timezone=True))
    cash_hours = Column(String(20))  # MORNING, AFTERNOON
    mpesa_number = Column(String(20))
    bank_account = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    items = relationship("ClaimItem", back_populates="claim", cascade="all, delete-orphan")

class ClaimItem(Base):
    __tablename__ = "claim_items"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    merchant_name = Column(String(255))
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(DateTime(timezone=True))
    category = Column(String(100))
    receipt_image_url = Column(Text)
    extracted_data = Column(JSON)

    # Relationships
    claim = relationship("Claim", back_populates="items")