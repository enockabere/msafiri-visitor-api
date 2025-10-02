# File: app/api/v1/api.py (UPDATE YOUR EXISTING ONE)
from fastapi import APIRouter
from app.api.v1.endpoints import auth, tenants, users, notifications, password, profile, tenant_users, events, super_admin, event_feedback, event_status, event_participants, event_attachments, invitations, roles_unified, auth_refresh, registration, emergency_contacts
from app.api.v1.endpoints import event_participants as event_participants_router
from app.api.v1.endpoints import event_attachments

# Create main API router
api_router = APIRouter()

# Include all endpoint routers with proper configuration
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["authentication"]
)

api_router.include_router(
    auth_refresh.router, 
    prefix="/auth", 
    tags=["authentication"]
)

api_router.include_router(
    registration.router,
    prefix="/registration",
    tags=["registration"]
)

api_router.include_router(
    password.router, 
    prefix="/password", 
    tags=["password-management"]
)

api_router.include_router(
    profile.router,
    prefix="/profile", 
    tags=["profile-management"]
)

api_router.include_router(
    emergency_contacts.router,
    prefix="/emergency-contacts",
    tags=["emergency-contacts"]
)

api_router.include_router(
    tenants.router, 
    prefix="/tenants", 
    tags=["tenants"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["users"]
)

api_router.include_router(
    notifications.router, 
    prefix="/notifications", 
    tags=["notifications"]
)

api_router.include_router(
    roles_unified.router,
    prefix="/roles",
    tags=["roles"]
)

api_router.include_router(
    tenant_users.router,
    prefix="/tenant-users",
    tags=["tenant-users"]
)

api_router.include_router(
    events.router,
    prefix="/events",
    tags=["events"]
)

api_router.include_router(
    event_participants_router.router,
    prefix="/events/{event_id}/participants",
    tags=["event-participants"]
)

api_router.include_router(
    event_attachments.router,
    prefix="/events/{event_id}/attachments",
    tags=["event-attachments"]
)

api_router.include_router(
    super_admin.router,
    prefix="/super-admin",
    tags=["super-admin"]
)



api_router.include_router(
    event_feedback.router,
    prefix="/events",
    tags=["event-feedback"]
)

api_router.include_router(
    event_status.router,
    prefix="/events",
    tags=["event-status"]
)

api_router.include_router(
    event_participants.router,
    prefix="/events/{event_id}/participants",
    tags=["event-participants"]
)

api_router.include_router(
    event_attachments.router,
    prefix="/events/{event_id}/attachments",
    tags=["event-attachments"]
)

from app.api.v1.endpoints import tenant_management
api_router.include_router(
    tenant_management.router,
    prefix="/tenant-management",
    tags=["tenant-management"]
)

api_router.include_router(
    invitations.router,
    prefix="/invitations",
    tags=["invitations"]
)

from app.api.v1.endpoints import security_briefings
api_router.include_router(
    security_briefings.router,
    prefix="/events/{event_id}/security-briefings",
    tags=["security-briefings"]
)

from app.api.v1.endpoints import event_agenda
api_router.include_router(
    event_agenda.router,
    prefix="/events/{event_id}/agenda",
    tags=["event-agenda"]
)

from app.api.v1.endpoints import inventory
api_router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["inventory"]
)

from app.api.v1.endpoints import event_registration
api_router.include_router(
    event_registration.router,
    prefix="/event-registration",
    tags=["event-registration"]
)

from app.api.v1.endpoints import attendance_confirmation
api_router.include_router(
    attendance_confirmation.router,
    prefix="/attendance",
    tags=["attendance-confirmation"]
)

from app.api.v1.endpoints import allocations
api_router.include_router(
    allocations.router,
    prefix="/allocations",
    tags=["allocations"]
)

from app.api.v1.endpoints import security_briefs
api_router.include_router(
    security_briefs.router,
    prefix="/security-briefings",
    tags=["security-briefings"]
)

from app.api.v1.endpoints import useful_contacts
api_router.include_router(
    useful_contacts.router,
    prefix="/useful-contacts",
    tags=["useful-contacts"]
)

from app.api.v1.endpoints import accommodation
api_router.include_router(
    accommodation.router,
    prefix="/accommodation",
    tags=["accommodation"]
)

from app.api.v1.endpoints import transport_booking
api_router.include_router(
    transport_booking.router,
    prefix="/transport",
    tags=["transport-booking"]
)

from app.api.v1.endpoints import user_roles
api_router.include_router(
    user_roles.router,
    prefix="/user-roles",
    tags=["user-roles"]
)

from app.api.v1.endpoints import participant_qr
api_router.include_router(
    participant_qr.router,
    prefix="/participants",
    tags=["participant-qr"]
)

from app.api.v1.endpoints import chat
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

# Add a test endpoint to verify the router works
@api_router.get("/", tags=["root"])
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "Msafiri API v1",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth - Authentication endpoints",
            "password": "/password - Password management",
            "profile": "/profile - User profile management",
            "users": "/users - User management", 
            "tenants": "/tenants - Tenant management",
            "notifications": "/notifications - Notification system",
            "roles": "/roles - Role management",
            "tenant-users": "/tenant-users - Tenant user management",
            "events": "/events - Event management",
            "event-participants": "/events/{id}/participants - Event participants and checklist",
            "event-allocations": "/events/{id}/items - Event item allocations and redemption",
            "event-speakers": "/events/speakers - Event speaker management",
            "participant-qr": "/participants - QR codes for participant allocations",
            "item-requests": "/participants - Item request workflow",
            "security-briefs": "/security-briefs - Security briefings and acknowledgments",
            "travel-management": "/travel - Participant tickets, welcome packages, and travel requirements",
            "chat": "/chat - Real-time chat rooms and direct messages"
        }
    }