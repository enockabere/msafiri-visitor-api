# File: app/schemas/user.py (COMPLETE REWRITE WITH FIXES)
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime, date
from app.models.user import UserRole, AuthProvider, UserStatus, Gender

# ==========================================
# TENANT ROLE SCHEMA
# ==========================================

class TenantRoleSchema(BaseModel):
    """Schema for user tenant roles"""
    tenant_id: Optional[int] = None  # Numeric tenant ID for API calls
    tenant_slug: str
    tenant_name: Optional[str] = None  # Tenant display name
    role: str

    class Config:
        from_attributes = True

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
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None

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

class ForcePasswordChangeRequest(BaseModel):
    """Schema for force changing password (no current password required)"""
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
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[str] = None
    profile_updated_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    
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
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issue_date: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    whatsapp_number: Optional[str] = None
    email_work: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Tenant roles
    tenant_roles: Optional[List[TenantRoleSchema]] = None
    
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
    missing_fields: List[str]  # FIXED: Changed from list[str] to List[str] for Python 3.8 compatibility

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
    basic_fields: List[str]  # FIXED: Changed from list[str] to List[str]
    enhanced_fields: List[str]  # FIXED: Changed from list[str] to List[str]
    readonly_fields: List[str]  # FIXED: Changed from list[str] to List[str]
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
    user_ids: List[int]  # FIXED: Changed from list[int] to List[int]
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

# ==========================================
# ROLE AND PERMISSION SCHEMAS
# ==========================================

class UserRoleChange(BaseModel):
    """Schema for changing user role"""
    new_role: UserRole
    reason: Optional[str] = None

class UserStatusChange(BaseModel):
    """Schema for changing user status"""
    is_active: bool
    status: UserStatus
    reason: Optional[str] = None

# ==========================================
# VALIDATION AND VERIFICATION SCHEMAS
# ==========================================

class EmailVerificationRequest(BaseModel):
    """Schema for requesting email verification"""
    email: EmailStr

class EmailVerificationConfirm(BaseModel):
    """Schema for confirming email verification"""
    token: str

class ProfileValidationErrors(BaseModel):
    """Schema for profile validation errors"""
    field_errors: dict
    global_errors: List[str]

# ==========================================
# EXPORT SCHEMAS FOR FRONTEND INTEGRATION
# ==========================================

class UserExport(BaseModel):
    """Schema for exporting user data"""
    include_sensitive: bool = False
    format: str = "json"  # json, csv, excel
    fields: Optional[List[str]] = None

class UserImport(BaseModel):
    """Schema for importing user data"""
    users: List[UserCreate]
    send_welcome_emails: bool = True
    auto_activate: bool = False

# ==========================================
# API RESPONSE WRAPPERS
# ==========================================

class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[User]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class ProfileUpdateResponse(BaseModel):
    """Response for profile updates"""
    success: bool
    user: User
    updated_fields: List[str]
    validation_errors: Optional[ProfileValidationErrors] = None

class SecurityAuditResponse(BaseModel):
    """Response for security audit"""
    user_id: int
    security_score: int  # 0-100
    recommendations: List[str]
    last_security_check: datetime

# ==========================================
# ADVANCED PROFILE FEATURES
# ==========================================

class ProfilePreferences(BaseModel):
    """User profile preferences"""
    language: str = "en"
    timezone: str = "UTC"
    email_notifications: bool = True
    push_notifications: bool = True
    theme: str = "light"  # light, dark, auto

class ProfileEmergencyContact(BaseModel):
    """Emergency contact information"""
    name: str
    relationship: str
    phone_number: str
    email: Optional[EmailStr] = None

class ProfileWorkDetails(BaseModel):
    """Work-related profile details"""
    employee_id: Optional[str] = None
    start_date: Optional[date] = None
    manager_email: Optional[EmailStr] = None
    office_location: Optional[str] = None
    cost_center: Optional[str] = None

# ==========================================
# COMPLETE EXTENDED PROFILE
# ==========================================

class ExtendedUserProfile(UserProfile):
    """Extended user profile with all possible fields"""
    preferences: Optional[ProfilePreferences] = None
    emergency_contact: Optional[ProfileEmergencyContact] = None
    work_details: Optional[ProfileWorkDetails] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[dict] = None
    
    # Compliance and legal
    gdpr_consent: Optional[datetime] = None
    terms_accepted: Optional[datetime] = None
    data_retention_consent: Optional[datetime] = None
