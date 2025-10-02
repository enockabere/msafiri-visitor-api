from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

class EmergencyContactBase(BaseModel):
    name: str
    relationship_type: str
    phone_number: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_primary: bool = False

class EmergencyContactCreate(EmergencyContactBase):
    pass

class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    relationship_type: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_primary: Optional[bool] = None

class EmergencyContact(EmergencyContactBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True