# File: app/schemas/__init__.py (UPDATED WITH ALL SCHEMAS)
from typing import Optional
from datetime import datetime
from .tenant import (
    Tenant, TenantCreate, TenantUpdate, TenantWithStats, 
    TenantEditRequest, TenantNotificationSettings
)
from .user import (
    # Base schemas
    User, UserCreate, UserUpdate, UserInDB, UserSSO, UserBase,
    
    # Profile management
    UserProfile, UserProfileUpdate, UserProfileBasic, ExtendedUserProfile,
    ProfileCompletion, SecurityStatus, ActivityInfo,
    EditableFieldsResponse, ProfileStatsResponse,
    
    # Password management
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    
    # User operations
    UserRoleChange, UserStatusChange, PendingApproval,
    UserBulkOperation, UserSearchFilters,
    
    # Validation and verification
    EmailVerificationRequest, EmailVerificationConfirm,
    ProfileValidationErrors,
    
    # Import/Export
    UserExport, UserImport, UserListResponse,
    ProfileUpdateResponse, SecurityAuditResponse,
    
    # Advanced features
    ProfilePreferences, ProfileEmergencyContact, ProfileWorkDetails
)
from .auth import Token, TokenData, LoginRequest
from .notification import (
    Notification, NotificationCreate, NotificationUpdate, NotificationStats,
    BroadcastNotification, UserNotification, TenantNotification,
    NotificationEdit, NotificationWithEditInfo
)

# Legacy compatibility - keep the basic schemas that were in the original __init__.py
class TenantWithStats(Tenant):
    """Tenant with statistics (basic version)"""
    total_users: int = 0
    active_users: int = 0
    pending_users: int = 0
    last_user_activity: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Export all schemas for easy imports
__all__ = [
    # Tenant schemas
    "Tenant", "TenantCreate", "TenantUpdate", "TenantWithStats", 
    "TenantEditRequest", "TenantNotificationSettings",
    
    # User core schemas
    "User", "UserCreate", "UserUpdate", "UserInDB", "UserSSO", "UserBase",
    
    # Profile management
    "UserProfile", "UserProfileUpdate", "UserProfileBasic", "ExtendedUserProfile",
    "ProfileCompletion", "SecurityStatus", "ActivityInfo",
    "EditableFieldsResponse", "ProfileStatsResponse",
    
    # Password management
    "PasswordChangeRequest", "PasswordResetRequest", "PasswordResetConfirm",
    
    # User operations
    "UserRoleChange", "UserStatusChange", "PendingApproval",
    "UserBulkOperation", "UserSearchFilters",
    
    # Validation and verification
    "EmailVerificationRequest", "EmailVerificationConfirm",
    "ProfileValidationErrors",
    
    # Import/Export
    "UserExport", "UserImport", "UserListResponse",
    "ProfileUpdateResponse", "SecurityAuditResponse",
    
    # Advanced features
    "ProfilePreferences", "ProfileEmergencyContact", "ProfileWorkDetails",
    
    # Auth schemas
    "Token", "TokenData", "LoginRequest",
    
    # Notification schemas
    "Notification", "NotificationCreate", "NotificationUpdate", "NotificationStats",
    "BroadcastNotification", "UserNotification", "TenantNotification",
    "NotificationEdit", "NotificationWithEditInfo"
]