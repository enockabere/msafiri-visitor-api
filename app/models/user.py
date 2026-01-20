# File: app/models/user.py (FIXED with extend_existing)
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, Date
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MT_ADMIN = "MT_ADMIN"
    HR_ADMIN = "HR_ADMIN"
    EVENT_ADMIN = "EVENT_ADMIN"
    VETTING_COMMITTEE = "VETTING_COMMITTEE"
    VETTING_APPROVER = "VETTING_APPROVER"
    VOUCHER_SCANNER = "VOUCHER_SCANNER"
    VISITOR = "VISITOR"
    GUEST = "GUEST"
    STAFF = "STAFF"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_EMAIL_VERIFICATION = "pending_email_verification"  # NEW

class AuthProvider(enum.Enum):
    LOCAL = "local"
    MICROSOFT_SSO = "microsoft_sso"
    GOOGLE_SSO = "google_sso"

class Gender(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # FIXED: Allow table redefinition
    
    # Basic auth fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.GUEST)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String, index=True, nullable=True)
    
    # SSO-specific fields
    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.LOCAL)
    external_id = Column(String(255), nullable=True, index=True)
    azure_tenant_id = Column(String(255), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # ENHANCED: Extended profile fields
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    nationality = Column(String(100), nullable=True)
    passport_number = Column(String(50), nullable=True)
    passport_issue_date = Column(Date, nullable=True)
    passport_expiry_date = Column(Date, nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    email_work = Column(String(255), nullable=True)  # Work email (can be different from login email)
    email_personal = Column(String(255), nullable=True)  # Personal email
    
    # Existing profile fields
    phone_number = Column(String(20), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    department = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # Event registration profile fields
    country = Column(String(100), nullable=True)
    position = Column(String(255), nullable=True)
    project = Column(String(255), nullable=True)
    
    # Auto-registration fields
    auto_registered = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # ENHANCED: Password management fields
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    must_change_password = Column(Boolean, default=False)
    
    # Profile update tracking
    profile_updated_at = Column(DateTime(timezone=True), nullable=True)
    profile_updated_by = Column(String(255), nullable=True)
    
    # Push notification token
    fcm_token = Column(String(500), nullable=True)
    
    # Relationships - commented out to avoid conflicts
    # profile = relationship("UserProfile", back_populates="user", uselist=False)
    # user_tenants = relationship("UserTenant", back_populates="user")
    emergency_contacts = relationship("EmergencyContact", back_populates="user")
    consents = relationship("UserConsent", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")