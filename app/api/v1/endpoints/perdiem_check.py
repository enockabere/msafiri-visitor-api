from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest
from app.models.event_participant import EventParticipant
from app.models.event import Event

router = APIRouter()

@router.get("/check-approver/{email}")
async def check_perdiem_approver(email: str, db: Session = Depends(get_db)):
    """Check if user email is designated as a per diem approver and return associated tenants"""
    
    # Check if the email appears as an approver in any per diem requests
    # Join with participant and event to get tenant information
    approver_requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        PerdiemRequest.approver_email == email
    ).all()
    
    if not approver_requests:
        return {
            "email": email,
            "is_approver": False,
            "tenants": []
        }
    
    # Get unique tenants from the events associated with per diem requests
    tenants = []
    for req in approver_requests:
        if req.participant and req.participant.event and req.participant.event.tenant_id:
            tenants.append(req.participant.event.tenant_id)
    
    # Remove duplicates
    tenants = list(set(tenants))
    
    return {
        "email": email,
        "is_approver": True,
        "tenants": tenants
    }