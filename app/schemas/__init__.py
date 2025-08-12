# File: app/schemas/__init__.py (MINIMAL WORKING VERSION)
from .tenant import Tenant, TenantCreate, TenantUpdate
from .user import User, UserCreate, UserUpdate, UserInDB, UserSSO
from .auth import Token, TokenData, LoginRequest
from .notification import Notification, NotificationCreate, NotificationUpdate, NotificationStats

# Add missing schemas as basic classes for now
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TenantWithStats(Tenant):
    """Tenant with statistics (basic version)"""
    total_users: int = 0
    active_users: int = 0
    pending_users: int = 0
    last_user_activity: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TenantEditRequest(BaseModel):
    """Request to edit tenant"""
    changes: TenantUpdate
    reason: str = "Updated by admin"
    notify_admins: bool = True

class UserProfile(User):
    """Extended user profile (basic version)"""
    has_strong_password: bool = False
    password_age_days: Optional[int] = None
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    # Enhanced fields (basic support)
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[str] = None
    email_personal: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str
    confirm_password: str

class PasswordResetRequest(BaseModel):
    """Schema for requesting password reset"""
    email: str

class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset"""
    token: str
    new_password: str
    confirm_password: str

# Add missing schemas to __all__
__all__ = [
    # Tenant schemas
    "Tenant", "TenantCreate", "TenantUpdate", "TenantWithStats", "TenantEditRequest",
    
    # User schemas
    "User", "UserCreate", "UserUpdate", "UserInDB", "UserSSO", "UserProfile",
    "UserProfileUpdate", "PasswordChangeRequest", "PasswordResetRequest", "PasswordResetConfirm",
    
    # Auth schemas
    "Token", "TokenData", "LoginRequest",
    
    # Notification schemas
    "Notification", "NotificationCreate", "NotificationUpdate", "NotificationStats"
]