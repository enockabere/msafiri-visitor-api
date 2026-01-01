from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class POATemplateBase(BaseModel):
    vendor_accommodation_id: int
    name: str
    description: Optional[str] = None
    template_content: str
    logo_url: Optional[str] = None
    logo_public_id: Optional[str] = None
    signature_url: Optional[str] = None
    signature_public_id: Optional[str] = None
    enable_qr_code: bool = True
    is_active: bool = True

class POATemplateCreate(POATemplateBase):
    pass

class POATemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    logo_url: Optional[str] = None
    logo_public_id: Optional[str] = None
    signature_url: Optional[str] = None
    signature_public_id: Optional[str] = None
    enable_qr_code: Optional[bool] = None
    is_active: Optional[bool] = None

class POATemplateResponse(POATemplateBase):
    id: int
    tenant_id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
