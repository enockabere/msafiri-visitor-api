# File: app/api/v1/api.py (UPDATE YOUR EXISTING ONE)
from fastapi import APIRouter, Depends
from app.api.v1.endpoints import auth, tenants, users, notifications, password, profile, tenant_users, events, super_admin, event_feedback, event_status, event_participants, event_attachments, invitations, roles_unified, auth_refresh, registration, emergency_contacts, user_consent, public_registration, auto_booking

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
    user_consent.router,
    prefix="/user-consent",
    tags=["user-consent"]
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
    event_participants.router,
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
    prefix="/events",
    tags=["event-agenda"]
)

# Add feedback endpoints separately to ensure they're accessible
from app.api.v1.endpoints import feedback
api_router.include_router(
    feedback.router,
    prefix="/events",
    tags=["feedback"]
)



from app.api.v1.endpoints import event_statistics
api_router.include_router(
    event_statistics.router,
    prefix="/events",
    tags=["event-statistics"]
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

api_router.include_router(
    public_registration.router,
    prefix="",
    tags=["public-registration"]
)

from app.api.v1.endpoints import public_qr
api_router.include_router(
    public_qr.router,
    prefix="",
    tags=["public-qr"]
)

api_router.include_router(
    auto_booking.router,
    prefix="/auto-booking",
    tags=["auto-booking"]
)

from app.api.v1.endpoints import participant_role_update
api_router.include_router(
    participant_role_update.router,
    prefix="/events",
    tags=["participant-role-update"]
)

from app.api.v1.endpoints import event_food
api_router.include_router(
    event_food.router,
    prefix="/events/{event_id}/food",
    tags=["event-food"]
)

from app.api.v1.endpoints import enhanced_feedback
api_router.include_router(
    enhanced_feedback.router,
    prefix="/events/{event_id}/feedback",
    tags=["enhanced-feedback"]
)

from app.api.v1.endpoints import countries
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
api_router.include_router(
    countries.router,
    prefix="/countries",
    tags=["countries"]
)

# Add registration email endpoint
@api_router.post("/notifications/send-registration-email")
async def send_registration_email(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Send registration link via email"""
    try:
        from app.core.email_service import email_service
        
        to_email = request_data.get("to_email")
        cc_emails = request_data.get("cc_emails", [])
        subject = request_data.get("subject")
        message = request_data.get("message")
        
        if not to_email or not subject or not message:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Send primary email
        email_service.send_notification_email(
            to_email=to_email,
            user_name=to_email.split('@')[0],
            title=subject,
            message=message
        )
        
        # Send CC emails
        for cc_email in cc_emails:
            if cc_email.strip():
                email_service.send_notification_email(
                    to_email=cc_email.strip(),
                    user_name=cc_email.split('@')[0],
                    title=subject,
                    message=message
                )
        
        return {
            "message": "Registration email sent successfully",
            "recipients": [to_email] + cc_emails
        }
        
    except Exception as e:
        print(f"Error sending registration email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

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