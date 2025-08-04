# File: app/models/user.py (CORRECTED - Lowercase to match database)
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    MT_ADMIN = "mt_admin"
    HR_ADMIN = "hr_admin"
    EVENT_ADMIN = "event_admin"
    VISITOR = "visitor"
    GUEST = "guest"
    STAFF = "staff"

class UserStatus(enum.Enum):
    # CORRECTED: Lowercase to match your database
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class AuthProvider(enum.Enum):
    # CORRECTED: Lowercase to match your database
    LOCAL = "local"
    MICROSOFT_SSO = "microsoft_sso"
    GOOGLE_SSO = "google_sso"

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.GUEST)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    phone_number = Column(String(20), nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
    
    # SSO-specific fields
    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.LOCAL)
    external_id = Column(String(255), nullable=True, index=True)
    azure_tenant_id = Column(String(255), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Profile fields
    profile_picture_url = Column(String(500), nullable=True)
    department = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # Auto-registration fields
    auto_registered = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)