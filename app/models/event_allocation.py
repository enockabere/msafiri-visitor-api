# File: app/models/event_allocation.py
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class ItemType(enum.Enum):
    PHYSICAL = "physical"  # pens, tshirts, etc.
    CONSUMABLE = "consumable"  # drinks, food, etc.

class EventItem(BaseModel):
    __tablename__ = "event_items"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    item_type = Column(Enum(ItemType), nullable=False)
    description = Column(String(500), nullable=True)
    total_quantity = Column(Integer, nullable=False, default=0)
    allocated_quantity = Column(Integer, nullable=False, default=0)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")

class ParticipantAllocation(BaseModel):
    __tablename__ = "participant_allocations"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("event_items.id"), nullable=False)
    allocated_quantity = Column(Integer, nullable=False, default=1)
    redeemed_quantity = Column(Integer, nullable=False, default=0)
    extra_requested = Column(Integer, nullable=False, default=0)
    allocated_by = Column(String(255), nullable=False)
    
    # Relationships
    participant = relationship("EventParticipant")
    item = relationship("EventItem")

class RedemptionLog(BaseModel):
    __tablename__ = "redemption_logs"
    
    allocation_id = Column(Integer, ForeignKey("participant_allocations.id"), nullable=False)
    quantity_redeemed = Column(Integer, nullable=False)
    redeemed_by = Column(String(255), nullable=False)  # Staff who gave the item
    notes = Column(String(500), nullable=True)
    
    # Relationships
    allocation = relationship("ParticipantAllocation")
