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
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm, ForcePasswordChangeRequest,
    
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
from .auth import Token, TokenData, LoginRequest, UserRegistrationRequest, UserRegistrationResponse, FCMTokenUpdate
from .notification import (
    Notification, NotificationCreate, NotificationUpdate, NotificationStats,
    BroadcastNotification, UserNotification, TenantNotification,
    NotificationEdit, NotificationWithEditInfo
)
from .role import Role, RoleCreate, RoleUpdate
from .event import Event, EventCreate, EventUpdate
from .event_participant import (
    EventParticipant, EventParticipantCreate, EventParticipantUpdate
)
from .event_allocation import (
    EventItem, EventItemCreate, ParticipantAllocation, ParticipantAllocationCreate,
    RedeemItemRequest, RequestExtraItemRequest, RedemptionLog, AllocateItemsRequest
)
from .admin_invitations import (
    AdminInvitationCreate, AdminInvitationResponse, AdminInvitationAccept
)
from .useful_contact import (
    UsefulContact, UsefulContactCreate, UsefulContactUpdate
)
from .accommodation import (
    GuestHouse, GuestHouseCreate, GuestHouseUpdate,
    Room, RoomCreate, RoomUpdate,
    VendorAccommodation, VendorAccommodationCreate, VendorAccommodationUpdate,
    AccommodationAllocation, AccommodationAllocationCreate, AccommodationAllocationUpdate,
    VendorEventAccommodation, VendorEventAccommodationCreate, VendorEventAccommodationUpdate,
    AccommodationType, RoomType, AllocationStatus
)
from .emergency_contact import (
    EmergencyContact, EmergencyContactCreate, EmergencyContactUpdate
)
from .user_consent import (
    UserConsent, UserConsentCreate, UserConsentUpdate
)
from .app_feedback import (
    AppFeedbackCreate, AppFeedbackResponse
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
    "PasswordChangeRequest", "PasswordResetRequest", "PasswordResetConfirm", "ForcePasswordChangeRequest",
    
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
    "NotificationEdit", "NotificationWithEditInfo",
    
    # Role schemas
    "Role", "RoleCreate", "RoleUpdate",
    
    # Event schemas
    "Event", "EventCreate", "EventUpdate",
    
    # Event participant schemas
    "EventParticipant", "EventParticipantCreate", "EventParticipantUpdate",
    
    # Event allocation schemas
    "EventItem", "EventItemCreate", "ParticipantAllocation", "ParticipantAllocationCreate",
    "RedeemItemRequest", "RequestExtraItemRequest", "RedemptionLog", "AllocateItemsRequest",
    
    # Admin invitation schemas
    "AdminInvitationCreate", "AdminInvitationResponse", "AdminInvitationAccept",
    
    # Useful contact schemas
    "UsefulContact", "UsefulContactCreate", "UsefulContactUpdate",
    
    # Accommodation schemas
    "GuestHouse", "GuestHouseCreate", "GuestHouseUpdate",
    "Room", "RoomCreate", "RoomUpdate",
    "VendorAccommodation", "VendorAccommodationCreate", "VendorAccommodationUpdate",
    "AccommodationAllocation", "AccommodationAllocationCreate", "AccommodationAllocationUpdate",
    "VendorEventAccommodation", "VendorEventAccommodationCreate", "VendorEventAccommodationUpdate",
    "AccommodationType", "RoomType", "AllocationStatus",
    
    # Emergency contact schemas
    "EmergencyContact", "EmergencyContactCreate", "EmergencyContactUpdate",
    
    # User consent schemas
    "UserConsent", "UserConsentCreate", "UserConsentUpdate",
    
    # App feedback schemas
    "AppFeedbackCreate", "AppFeedbackResponse"
]