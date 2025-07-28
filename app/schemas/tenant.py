from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class TenantBase(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None
    contact_email: EmailStr
    description: Optional[str] = None
    
class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    
class Tenant(TenantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True