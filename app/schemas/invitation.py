# File: app/schemas/invitation.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class InvitationBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    tenant_id: str

class InvitationCreate(InvitationBase):
    pass

class InvitationUpdate(BaseModel):
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    is_accepted: Optional[str] = None

class Invitation(InvitationBase):
    id: int
    token: str
    expires_at: datetime
    invited_by: str
    accepted_at: Optional[datetime] = None
    is_accepted: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
