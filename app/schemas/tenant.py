# File: app/schemas/tenant.py (ENHANCED)
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class TenantBase(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None
    contact_email: EmailStr
    description: Optional[str] = None
    admin_email: Optional[EmailStr] = None  # Primary admin for notifications
    phone_number: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    
class TenantCreate(TenantBase):
    # Settings for new tenant
    allow_self_registration: bool = False
    require_admin_approval: bool = True
    max_users: Optional[str] = "unlimited"
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug can only contain letters, numbers, hyphens, and underscores')
        if len(v) < 3:
            raise ValueError('Slug must be at least 3 characters long')
        return v.lower()

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    admin_email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    allow_self_registration: Optional[bool] = None
    require_admin_approval: Optional[bool] = None
    max_users: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    
    @validator('primary_color')
    def validate_color(cls, v):
        if v and not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be in hex format (#RRGGBB)')
        return v
    
class Tenant(TenantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Enhanced fields
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    allow_self_registration: bool = False
    require_admin_approval: bool = True
    max_users: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    last_notification_sent: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TenantWithStats(Tenant):
    """Tenant with user statistics"""
    total_users: int = 0
    active_users: int = 0
    pending_users: int = 0
    last_user_activity: Optional[datetime] = None

class TenantNotificationSettings(BaseModel):
    """Settings for tenant notifications"""
    tenant_id: int
    primary_admin_email: EmailStr
    additional_emails: List[EmailStr] = []
    notify_on_user_registration: bool = True
    notify_on_user_approval_needed: bool = True
    notify_on_tenant_changes: bool = True
    
class TenantEditRequest(BaseModel):
    """Request to edit tenant details"""
    changes: TenantUpdate
    reason: str  # Reason for the change
    notify_admins: bool = True