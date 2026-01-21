from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PrivacyPolicyBase(BaseModel):
    title: str = "Privacy Policy"
    content: Optional[str] = None
    document_url: Optional[str] = None
    document_public_id: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[datetime] = None

class PrivacyPolicyCreate(PrivacyPolicyBase):
    pass

class PrivacyPolicyUpdate(PrivacyPolicyBase):
    title: Optional[str] = None

class PrivacyPolicyResponse(PrivacyPolicyBase):
    id: int
    is_active: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True