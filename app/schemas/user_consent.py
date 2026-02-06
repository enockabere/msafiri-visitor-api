from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class UserConsentBase(BaseModel):
    data_protection_accepted: bool = False
    terms_conditions_accepted: bool = False
    data_protection_version: Optional[str] = None
    terms_conditions_version: Optional[str] = None
    data_protection_link: Optional[str] = None
    terms_conditions_link: Optional[str] = None

class UserConsentCreate(UserConsentBase):
    pass

class UserConsentUpdate(BaseModel):
    data_protection_accepted: Optional[bool] = None
    terms_conditions_accepted: Optional[bool] = None
    data_protection_version: Optional[str] = None
    terms_conditions_version: Optional[str] = None
    data_protection_link: Optional[str] = None
    terms_conditions_link: Optional[str] = None

class UserConsent(UserConsentBase):
    id: int
    user_id: int
    tenant_id: str
    data_protection_accepted_at: Optional[datetime] = None
    terms_conditions_accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
