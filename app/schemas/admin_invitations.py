from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class AdminInvitationCreate(BaseModel):
    email: EmailStr

class AdminInvitationResponse(BaseModel):
    id: int
    email: str
    invited_by: str
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    user_existed: bool
    
    class Config:
        from_attributes = True

class AdminInvitationAccept(BaseModel):
    token: str
    password: Optional[str] = None  # Only needed if user doesn't exist
