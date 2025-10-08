# File: app/schemas/inventory.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class InventoryBase(BaseModel):
    name: str
    category: str  # 'stationary' or 'equipment'
    quantity: int = 0
    condition: str = 'good'

class InventoryCreate(InventoryBase):
    tenant_id: int

class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    condition: Optional[str] = None

class Inventory(InventoryBase):
    id: int
    tenant_id: int
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True