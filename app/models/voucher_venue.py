# File: app/models/voucher_venue.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime


class VoucherVenue(Base):
    """Links voucher allocations to valid redemption venues (vendor hotels)"""
    __tablename__ = "voucher_venues"

    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("event_allocations.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    # Relationships
    allocation = relationship("EventAllocation", back_populates="venues")
    vendor_accommodation = relationship("VendorAccommodation")
