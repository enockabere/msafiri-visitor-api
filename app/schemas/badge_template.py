from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class BadgeTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_content: Optional[str] = None
    logo_url: Optional[str] = None
    logo_public_id: Optional[str] = None
    background_url: Optional[str] = None
    background_public_id: Optional[str] = None
    enable_qr_code: bool = True
    is_active: bool = True
    badge_size: str = "standard"
    orientation: str = "portrait"
    contact_phone: Optional[str] = None
    website_url: Optional[str] = None
    avatar_url: Optional[str] = None
    include_avatar: bool = False


class BadgeTemplateCreate(BadgeTemplateBase):
    pass


class BadgeTemplateUpdate(BadgeTemplateBase):
    name: Optional[str] = None
    enable_qr_code: Optional[bool] = None
    is_active: Optional[bool] = None
    badge_size: Optional[str] = None
    orientation: Optional[str] = None
    contact_phone: Optional[str] = None
    website_url: Optional[str] = None
    avatar_url: Optional[str] = None
    include_avatar: Optional[bool] = None


class BadgeTemplate(BadgeTemplateBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True