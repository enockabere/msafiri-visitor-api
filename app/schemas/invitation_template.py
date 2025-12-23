from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class InvitationTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_content: str
    logo_url: Optional[str] = None
    logo_public_id: Optional[str] = None
    watermark_url: Optional[str] = None
    watermark_public_id: Optional[str] = None
    signature_url: Optional[str] = None
    signature_public_id: Optional[str] = None
    enable_qr_code: bool = True
    is_active: bool = True
    address_fields: Optional[List[str]] = []
    signature_footer_fields: Optional[List[str]] = []

class InvitationTemplateCreate(InvitationTemplateBase):
    pass

class InvitationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    logo_url: Optional[str] = None
    logo_public_id: Optional[str] = None
    watermark_url: Optional[str] = None
    watermark_public_id: Optional[str] = None
    signature_url: Optional[str] = None
    signature_public_id: Optional[str] = None
    enable_qr_code: Optional[bool] = None
    is_active: Optional[bool] = None
    address_fields: Optional[List[str]] = None
    signature_footer_fields: Optional[List[str]] = None

class InvitationTemplate(InvitationTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True