# File: app/models/allocation.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class EventAllocation(Base):
    __tablename__ = "event_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity_per_participant = Column(Integer, nullable=False)
    drink_vouchers_per_participant = Column(Integer, default=0)  # Keep for backward compatibility
    voucher_type = Column(String, nullable=True)  # New field for voucher type
    vouchers_per_participant = Column(Integer, default=0)  # New generic voucher field
    status = Column(String, default="open")  # open, pending, approved, rejected
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(String, nullable=False)
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships
    inventory_item = relationship("Inventory")
