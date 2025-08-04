from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole, AuthProvider, UserStatus

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.GUEST
    department: Optional[str] = None
    job_title: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None  # Optional for SSO users
    tenant_id: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.LOCAL
    external_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[UserStatus] = None

class UserSSO(BaseModel):
    """Schema for SSO user creation/update"""
    email: EmailStr
    full_name: str
    external_id: str
    auth_provider: AuthProvider
    azure_tenant_id: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    profile_picture_url: Optional[str] = None
    tenant_id: Optional[str] = None

class User(UserBase):
    id: int
    tenant_id: Optional[str] = None
    status: UserStatus
    is_active: bool
    auth_provider: AuthProvider
    external_id: Optional[str] = None
    auto_registered: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: Optional[str] = None

class PendingApproval(BaseModel):
    """Schema for pending approval notifications"""
    user: User
    days_pending: int
    tenant_name: Optional[str] = None