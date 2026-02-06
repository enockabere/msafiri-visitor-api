# File: app/schemas/allocation.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AllocationItem(BaseModel):
    inventory_item_id: int
    quantity_per_event: int

class AllocationBase(BaseModel):
    event_id: int
    inventory_item_id: int
    quantity_per_participant: int
    drink_vouchers_per_participant: int = 0  # Keep for backward compatibility
    voucher_type: Optional[str] = None  # New field
    vouchers_per_participant: int = 0  # New field
    notes: Optional[str] = None
    status: Optional[str] = "open"

class AllocationCreate(BaseModel):
    event_id: int
    items: Optional[List[AllocationItem]] = []
    drink_vouchers_per_participant: int = 0  # Keep for backward compatibility
    voucher_type: Optional[str] = None  # New field
    vouchers_per_participant: int = 0  # New field
    notes: Optional[str] = None
    status: Optional[str] = "open"

class AllocationUpdate(BaseModel):
    items: Optional[List[AllocationItem]] = None
    drink_vouchers_per_participant: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class AllocationItemResponse(BaseModel):
    inventory_item_id: int
    quantity_per_event: int
    inventory_item_name: str
    available_quantity: int

class Allocation(BaseModel):
    id: int
    event_id: int
    items: List[AllocationItemResponse]
    drink_vouchers_per_participant: int = 0  # Keep for backward compatibility
    voucher_type: Optional[str] = None  # New field
    vouchers_per_participant: int = 0  # New field
    status: str
    notes: Optional[str] = None
    tenant_id: int
    created_by: str
    approved_by: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
