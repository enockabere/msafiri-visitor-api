from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.tenant import Tenant

router = APIRouter()

@router.get("/check-approver/{email}")
async def check_perdiem_approver(email: str, db: Session = Depends(get_db)):
    """Check if user email is designated as a per diem approver and return associated tenant slugs"""

    # Check if the email appears as an approver in any per diem requests
    # Join with participant, event, and tenant to get tenant slug
    approver_requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).join(
        Tenant, Event.tenant_id == Tenant.id
    ).filter(
        PerdiemRequest.approver_email == email
    ).options(
        joinedload(PerdiemRequest.participant).joinedload(EventParticipant.event).joinedload(Event.tenant)
    ).all()

    if not approver_requests:
        return {
            "email": email,
            "is_approver": False,
            "tenants": []
        }

    # Get unique tenant slugs from the events associated with per diem requests
    tenants = []
    for req in approver_requests:
        if req.participant and req.participant.event and req.participant.event.tenant:
            tenants.append(req.participant.event.tenant.slug)

    # Remove duplicates
    tenants = list(set(tenants))

    return {
        "email": email,
        "is_approver": True,
        "tenants": tenants
    }