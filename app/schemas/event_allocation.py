# File: app/schemas/event_allocation.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.event_allocation import ItemType

class EventItemBase(BaseModel):
    item_name: str
    item_type: ItemType
    description: Optional[str] = None
    total_quantity: int

class EventItemCreate(EventItemBase):
    pass

class EventItem(EventItemBase):
    id: int
    event_id: int
    allocated_quantity: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ParticipantAllocationBase(BaseModel):
    allocated_quantity: int = 1

class ParticipantAllocationCreate(ParticipantAllocationBase):
    participant_id: int
    item_id: int

class ParticipantAllocation(ParticipantAllocationBase):
    id: int
    participant_id: int
    item_id: int
    redeemed_quantity: int
    extra_requested: int
    allocated_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RedeemItemRequest(BaseModel):
    allocation_id: int
    quantity: int = 1
    notes: Optional[str] = None

class RequestExtraItemRequest(BaseModel):
    allocation_id: int
    extra_quantity: int = 1

class RedemptionLog(BaseModel):
    id: int
    allocation_id: int
    quantity_redeemed: int
    redeemed_by: str
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AllocateItemsRequest(BaseModel):
    item_id: int
    participant_ids: List[int]
    quantity_per_participant: int = 1