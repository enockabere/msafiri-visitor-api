# File: app/schemas/inventory.py
from typing import Optional, Union
from pydantic import BaseModel, field_validator
from datetime import datetime

class InventoryBase(BaseModel):
    name: str
    category: str  # 'stationary' or 'equipment'
    quantity: int = 0
    condition: str = 'good'

class InventoryCreate(InventoryBase):
    tenant_id: Union[int, str]
    
    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v

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
