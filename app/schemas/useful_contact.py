from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UsefulContactBase(BaseModel):
    name: str
    position: str
    email: EmailStr
    phone: Optional[str] = None
    department: Optional[str] = None

class UsefulContactCreate(UsefulContactBase):
    pass

class UsefulContactUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None

class UsefulContact(UsefulContactBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str

    class Config:
        from_attributes = True