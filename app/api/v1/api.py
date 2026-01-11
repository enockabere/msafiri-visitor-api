# File: app/api/v1/api.py (UPDATE YOUR EXISTING ONE)
from fastapi import APIRouter, Depends
from app.api.v1.endpoints import auth, tenants, users, notifications, password, profile, tenant_users, events, super_admin, event_feedback, event_status, event_participants, event_attachments, invitations, roles_unified, auth_refresh, registration, emergency_contacts, user_consent, public_registration, auto_booking, password_reset, upload, vetting_committee, code_of_conduct, participant_response, form_fields, user_preferences
from app.api.v1 import vetting
from app.api import deps

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
    password_reset.router,
    prefix="/password",
    tags=["password-reset"]
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
    vetting_committee.router,
    prefix="/vetting-committee",
    tags=["vetting-committee"]
)

api_router.include_router(
    vetting.router,
    prefix="",
    tags=["vetting"]
)

from app.api.v1.endpoints import vetting_export
api_router.include_router(
    vetting_export.router,
    prefix="/vetting-committee",
    tags=["vetting-export"]
)

api_router.include_router(
    code_of_conduct.router,
    prefix="/code-of-conduct",
    tags=["code-of-conduct"]
)

api_router.include_router(
    participant_response.router,
    prefix="/participant-response",
    tags=["participant-response"]
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

# Upload endpoints for email images to Azure Blob Storage
api_router.include_router(
    upload.router,
    prefix="/upload",
    tags=["upload"]
)

# Document upload endpoints for Cloudinary
from app.api.v1.endpoints import documents
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

# Badge templates
from app.api.v1.endpoints import badge_templates
api_router.include_router(
    badge_templates.router,
    prefix="/tenants/{tenant_slug}/badge-templates",
    tags=["badge-templates"]
)

# Also add badge templates without tenant prefix for generate endpoint
api_router.include_router(
    badge_templates.router,
    prefix="/badge-templates",
    tags=["badge-templates-generate"]
)

# Certificate templates
from app.api.v1.endpoints import certificate_templates
api_router.include_router(
    certificate_templates.router,
    prefix="/certificate-templates",
    tags=["certificate-templates"]
)

# Invitation templates (with generate endpoint)
from app.api.v1.endpoints import invitation_templates
api_router.include_router(
    invitation_templates.router,
    prefix="/tenants/{tenant_slug}/invitation-templates",
    tags=["invitation-templates"]
)

# Also add invitation templates without tenant prefix for generate endpoint
api_router.include_router(
    invitation_templates.router,
    prefix="/invitation-templates",
    tags=["invitation-templates-generate"]
)

# LOI generation endpoint (separate from tenant-specific templates)
from app.api.v1.endpoints import loi
api_router.include_router(
    loi.router,
    prefix="/invitation-templates",
    tags=["loi-generation"]
)

# LOI generation for events
from app.api.v1.endpoints import loi_generation
api_router.include_router(
    loi_generation.router,
    prefix="",
    tags=["loi-generation"]
)

# POA (Proof of Accommodation) templates
from app.api.v1.endpoints import poa_templates
api_router.include_router(
    poa_templates.router,
    prefix="/poa-templates",
    tags=["poa-templates"]
)

# Event certificates
from app.api.v1.endpoints import event_certificates
api_router.include_router(
    event_certificates.router,
    prefix="/events",
    tags=["event-certificates"]
)

# Also include event certificates without prefix for direct certificate access
api_router.include_router(
    event_certificates.router,
    prefix="",
    tags=["certificates-direct"]
)

# Event badges
from app.api.v1.endpoints import event_badges
api_router.include_router(
    event_badges.router,
    prefix="/events",
    tags=["event-badges"]
)

# Also include badges without prefix for direct badge access
api_router.include_router(
    event_badges.router,
    prefix="",
    tags=["badges-direct"]
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

from app.api.v1.endpoints import auto_transport
api_router.include_router(
    auto_transport.router,
    prefix="/transport",
    tags=["auto-transport"]
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
    prefix="/public-registration",
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

from app.api.v1.endpoints import line_manager_recommendation
api_router.include_router(
    line_manager_recommendation.router,
    prefix="/line-manager-recommendation",
    tags=["line-manager-recommendation"]
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

# Add room stats endpoint
from app.api.v1.endpoints import room_stats
api_router.include_router(
    room_stats.router,
    prefix="/events",
    tags=["room-stats"]
)

# Add accommodation stats endpoint
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.db.database import get_db
from app.models.event import Event

@api_router.get("/events/{event_id}/accommodation-stats")
def get_event_accommodation_stats(event_id: int, db: Session = Depends(get_db)):
    """Get accommodation booking statistics for an event"""
    
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get participant statistics during migration period
    try:
        # Count confirmed participants as "bookings needed"
        confirmed_result = db.execute(text("""
            SELECT COUNT(*) as confirmed_count
            FROM event_participants ep
            WHERE ep.event_id = :event_id AND ep.status = 'confirmed'
        """), {"event_id": event_id})
        
        confirmed_count = confirmed_result.fetchone().confirmed_count or 0
        
        # Try to get actual bookings from accommodation_allocations table
        booking_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_bookings,
                COUNT(CASE WHEN aa.status = 'checked_in' THEN 1 END) as checked_in_visitors,
                COUNT(CASE WHEN aa.status = 'released' THEN 1 END) as checked_out_visitors
            FROM accommodation_allocations aa
            JOIN event_participants ep ON aa.participant_id = ep.id
            WHERE ep.event_id = :event_id AND aa.status IN ('booked', 'checked_in', 'released')
        """), {"event_id": event_id})
        
        booking_stats = booking_result.fetchone()
        
        return {
            "total_bookings": booking_stats.total_bookings or confirmed_count,
            "booked_rooms": booking_stats.total_bookings or confirmed_count,
            "checked_in_visitors": booking_stats.checked_in_visitors or 0,
            "checked_out_visitors": booking_stats.checked_out_visitors or 0
        }
    except Exception:
        # Fallback: count confirmed participants
        try:
            confirmed_result = db.execute(text("""
                SELECT COUNT(*) as confirmed_count
                FROM event_participants ep
                WHERE ep.event_id = :event_id AND ep.status = 'confirmed'
            """), {"event_id": event_id})
            
            confirmed_count = confirmed_result.fetchone().confirmed_count or 0
            
            return {
                "total_bookings": confirmed_count,
                "booked_rooms": confirmed_count,
                "checked_in_visitors": 0
            }
        except Exception:
            return {
                "total_bookings": 0,
                "booked_rooms": 0,
                "checked_in_visitors": 0
            }



from app.api.v1.endpoints import countries
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
api_router.include_router(
    countries.router,
    prefix="/countries",
    tags=["countries"]
)

from app.api.v1.endpoints import country_travel_requirements
api_router.include_router(
    country_travel_requirements.router,
    prefix="/country-travel-requirements",
    tags=["country-travel-requirements"]
)

from app.api.v1.endpoints import transport_providers
api_router.include_router(
    transport_providers.router,
    prefix="/transport-providers",
    tags=["transport-providers"]
)

# Guest house stub endpoints (functionality disabled due to model conflicts)
from app.api.v1.endpoints import guest_houses_stub
api_router.include_router(
    guest_houses_stub.router,
    prefix="/guest-houses",
    tags=["guest-houses-stub"]
)

from app.api.v1.endpoints import accommodation_refresh
api_router.include_router(
    accommodation_refresh.router,
    prefix="/accommodation",
    tags=["accommodation-refresh"]
)

from app.api.v1.endpoints import confirmed_guests
api_router.include_router(
    confirmed_guests.router,
    prefix="/accommodation",
    tags=["confirmed-guests"]
)

from app.api.v1.endpoints import absolute_transport
api_router.include_router(
    absolute_transport.router,
    prefix="/transport",
    tags=["absolute-transport"]
)

from app.api.v1.endpoints import test_data
api_router.include_router(
    test_data.router,
    prefix="/test-data",
    tags=["test-data"]
)

from app.api.v1.endpoints import app_feedback
api_router.include_router(
    app_feedback.router,
    prefix="/app-feedback",
    tags=["app-feedback"]
)

from app.api.v1.endpoints import news_updates
api_router.include_router(
    news_updates.router,
    prefix="/news-updates",
    tags=["news-updates"]
)

from app.api.v1.endpoints import passport_upload
api_router.include_router(
    passport_upload.router,
    prefix="/passport",
    tags=["passport-upload"]
)

from app.api.v1.endpoints import flight_itinerary
api_router.include_router(
    flight_itinerary.router,
    prefix="/flight-itinerary",
    tags=["flight-itinerary"]
)

from app.api.v1.endpoints import tenant
api_router.include_router(
    tenant.router,
    prefix="/tenants",
    tags=["tenant-lookup"]
)

from app.api.v1.endpoints import travel_checklist
api_router.include_router(
    travel_checklist.router,
    prefix="/travel-checklist",
    tags=["travel-checklist"]
)

from app.api.v1.endpoints import google_maps
api_router.include_router(
    google_maps.router,
    prefix="/google-maps",
    tags=["google-maps"]
)

from app.api.v1.endpoints import transport_request
api_router.include_router(
    transport_request.router,
    prefix="",
    tags=["transport-request"]
)

# Also include under /transport prefix for mobile app compatibility
api_router.include_router(
    transport_request.router,
    prefix="/transport",
    tags=["transport-request-mobile"]
)

from app.api.v1.endpoints import loi
api_router.include_router(
    loi.router,
    prefix="/loi",
    tags=["loi"]
)

from app.api.v1.endpoints import mobile_allocations
api_router.include_router(
    mobile_allocations.router,
    prefix="/mobile-allocations",
    tags=["mobile-allocations"]
)

# Voucher endpoints
from app.api.v1.endpoints import voucher_scanners
api_router.include_router(
    voucher_scanners.router,
    prefix="",
    tags=["voucher-scanners"]
)

from app.api.v1.endpoints import voucher_redemptions
api_router.include_router(
    voucher_redemptions.router,
    prefix="",
    tags=["voucher-redemptions"]
)

from app.api.v1.endpoints import scanner_dashboard
api_router.include_router(
    scanner_dashboard.router,
    prefix="",
    tags=["scanner-dashboard"]
)

from app.api.v1.endpoints import scanner
api_router.include_router(
    scanner.router,
    prefix="",
    tags=["scanner"]
)

from app.api.v1.endpoints import admin_cleanup
api_router.include_router(
    admin_cleanup.router,
    prefix="/admin",
    tags=["admin-cleanup"]
)

# Participant proof of accommodation endpoint
from app.api.v1.endpoints import participant_proof
api_router.include_router(
    participant_proof.router,
    prefix="",
    tags=["participant-proof"]
)

# Vendor proof generation endpoint
from app.api.v1.endpoints import vendor_proof_generation
api_router.include_router(
    vendor_proof_generation.router,
    prefix="",
    tags=["vendor-proof"]
)

# Certificate generation endpoints
from app.api.v1.endpoints import certificates
api_router.include_router(
    certificates.router,
    prefix="",
    tags=["certificates"]
)

# Event certificate generation
from app.api.v1.endpoints import event_certificate_generation
api_router.include_router(
    event_certificate_generation.router,
    prefix="",
    tags=["event-certificate-generation"]
)

# Event badge generation
from app.api.v1.endpoints import event_badge_generation
api_router.include_router(
    event_badge_generation.router,
    prefix="",
    tags=["event-badge-generation"]
)

# Participant documents (certificates and badges)
from app.api.v1.endpoints import participant_documents
api_router.include_router(
    participant_documents.router,
    prefix="/participant-documents",
    tags=["participant-documents"]
)

# Form fields for dynamic forms
api_router.include_router(
    form_fields.router,
    prefix="/form-fields",
    tags=["form-fields"]
)

api_router.include_router(
    user_preferences.router,
    prefix="/user-preferences",
    tags=["user-preferences"]
)

# Email templates
from app.api.v1.endpoints import email_templates
api_router.include_router(
    email_templates.router,
    prefix="/email-templates",
    tags=["email-templates"]
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

# Add event participants permissions endpoint for frontend compatibility
@api_router.get("/event-participants/permissions")
def get_event_participant_permissions(
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user)
):
    """Get event participant edit permissions - frontend compatibility endpoint"""
    from app.core.permissions import can_edit_vetting_participants
    from app.models.user import UserRole
    from app.models.vetting_committee import VettingCommittee, VettingStatus
    
    has_admin_permission = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    has_vetting_permission = can_edit_vetting_participants(current_user, db, event_id)
    
    # Get vetting status for frontend
    committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()
    
    vetting_status = None
    can_approve_vetting = False
    
    if committee:
        vetting_status = committee.status.value if committee.status else None
        # Check if current user can approve vetting
        can_approve_vetting = (
            current_user.role == UserRole.VETTING_APPROVER and 
            committee.approver_email == current_user.email and
            committee.status == VettingStatus.SUBMITTED_FOR_APPROVAL
        )
    
    return {
        "can_edit": has_admin_permission or has_vetting_permission,
        "has_admin_permission": has_admin_permission,
        "has_vetting_permission": has_vetting_permission,
        "vetting_status": vetting_status,
        "can_approve_vetting": can_approve_vetting
    }

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