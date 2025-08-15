# File: app/schemas/user.py (COMPLETE REWRITE)
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, date
from app.models.user import UserRole, AuthProvider, UserStatus

# ==========================================
# BASE SCHEMAS
# ==========================================

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.GUEST
    department: Optional[str] = None
    job_title: Optional[str] = None

# ==========================================
# PROFILE UPDATE SCHEMAS
# ==========================================

class UserProfileUpdate(BaseModel):
    """Schema for updating user profile information"""
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[EmailStr] = None
    email_personal: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    
    @validator('passport_expiry_date')
    def validate_passport_expiry(cls, v, values):
        if v and 'passport_issue_date' in values and values['passport_issue_date']:
            if v <= values['passport_issue_date']:
                raise ValueError('Passport expiry date must be after issue date')
        return v
    
    @validator('date_of_birth')
    def validate_dob(cls, v):
        if v and v >= date.today():
            raise ValueError('Date of birth must be in the past')
        return v

# ==========================================
# PASSWORD MANAGEMENT SCHEMAS
# ==========================================

class PasswordChangeRequest(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class PasswordResetRequest(BaseModel):
    """Schema for requesting password reset"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset"""
    token: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# ==========================================
# USER CRUD SCHEMAS
# ==========================================

class UserCreate(UserBase):
    """Schema for creating new users"""
    password: Optional[str] = None
    tenant_id: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.LOCAL
    external_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None

class UserUpdate(BaseModel):
    """Schema for updating existing users"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[UserStatus] = None

class UserSSO(BaseModel):
    """Schema for SSO user registration"""
    email: EmailStr
    full_name: str
    external_id: str
    auth_provider: AuthProvider
    azure_tenant_id: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    profile_picture_url: Optional[str] = None
    tenant_id: Optional[str] = None

# ==========================================
# USER RESPONSE SCHEMAS
# ==========================================

class User(UserBase):
    """Standard user response schema"""
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
    
    # Enhanced profile fields
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[str] = None
    email_personal: Optional[str] = None
    profile_updated_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserInDB(User):
    """User schema with password hash (for internal use)"""
    hashed_password: Optional[str] = None

# ==========================================
# PROFILE RESPONSE SCHEMA - FIXED
# ==========================================

class UserProfile(BaseModel):
    """Complete user profile response - matches frontend UserProfile type"""
    id: int
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    tenant_id: Optional[str] = None
    
    # CRITICAL: Core user properties (these were missing)
    is_active: bool
    auth_provider: AuthProvider
    external_id: Optional[str] = None
    auto_registered: bool = False
    
    # Basic profile information
    phone_number: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    
    # Enhanced profile information
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[str] = None
    email_personal: Optional[str] = None
    
    # Timestamps and metadata
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    profile_updated_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    
    # Security indicators
    has_strong_password: bool = False
    password_age_days: Optional[int] = None
    
    class Config:
        from_attributes = True

# ==========================================
# PROFILE MANAGEMENT RESPONSE SCHEMAS
# ==========================================

class ProfileCompletion(BaseModel):
    """Profile completion information"""
    percentage: int
    completed_fields: int
    total_basic_fields: int
    missing_fields: list[str]

class SecurityStatus(BaseModel):
    """Security status information"""
    auth_method: str
    has_password: bool
    password_age_days: Optional[int] = None
    email_verified: bool

class ActivityInfo(BaseModel):
    """Activity tracking information"""
    profile_last_updated: Optional[str] = None
    password_last_changed: Optional[str] = None

class EditableFieldsResponse(BaseModel):
    """Response from editable fields endpoint"""
    basic_fields: list[str]
    enhanced_fields: list[str]
    readonly_fields: list[str]
    can_change_password: bool
    profile_completion: ProfileCompletion

class ProfileStatsResponse(BaseModel):
    """Response from profile stats endpoint"""
    account_age_days: int
    last_login: Optional[str] = None
    profile_completion: ProfileCompletion
    security_status: SecurityStatus
    activity: ActivityInfo

# ==========================================
# ADDITIONAL UTILITY SCHEMAS
# ==========================================

class PendingApproval(BaseModel):
    """Schema for pending user approvals"""
    user: User
    days_pending: int
    tenant_name: Optional[str] = None

class UserProfileBasic(BaseModel):
    """Minimal user profile for listings"""
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserBulkOperation(BaseModel):
    """Schema for bulk user operations"""
    user_ids: list[int]
    operation: str  
    reason: Optional[str] = None

class UserSearchFilters(BaseModel):
    """Schema for user search filters"""
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    tenant_id: Optional[str] = None
    is_active: Optional[bool] = None
    auth_provider: Optional[AuthProvider] = None
    department: Optional[str] = None
    search_term: Optional[str] = None  