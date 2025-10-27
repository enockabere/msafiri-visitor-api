from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api import deps
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.tenant import Tenant
from datetime import datetime

router = APIRouter()

@router.post("/create-test-international-visitors")
async def create_test_international_visitors(
    tenant_context: str,
    current_user = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Create test international visitors for transport demo"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get the first event for this tenant
    event = db.query(Event).filter(Event.tenant_id == tenant.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="No events found for tenant")
    
    # Test participants data
    test_participants = [
        {
            "full_name": "John Kamau",
            "email": "john.kamau@msf.org",
            "travelling_from_country": "Uganda",
            "status": "confirmed"
        },
        {
            "full_name": "Sarah Mwangi",
            "email": "sarah.mwangi@msf.org", 
            "travelling_from_country": "Tanzania",
            "status": "confirmed"
        },
        {
            "full_name": "Ahmed Hassan",
            "email": "ahmed.hassan@msf.org",
            "travelling_from_country": "Ethiopia", 
            "status": "confirmed"
        },
        {
            "full_name": "Grace Nyong",
            "email": "grace.nyong@msf.org",
            "travelling_from_country": "South Sudan",
            "status": "confirmed"
        },
        {
            "full_name": "Mohamed Ali",
            "email": "mohamed.ali@msf.org",
            "travelling_from_country": "Somalia",
            "status": "confirmed"
        }
    ]
    
    created_participants = []
    
    for participant_data in test_participants:
        # Check if participant already exists
        existing = db.query(EventParticipant).filter(
            EventParticipant.event_id == event.id,
            EventParticipant.email == participant_data["email"]
        ).first()
        
        if not existing:
            # Create new participant
            participant = EventParticipant(
                event_id=event.id,
                full_name=participant_data["full_name"],
                email=participant_data["email"],
                travelling_from_country=participant_data["travelling_from_country"],
                status=participant_data["status"],
                role="attendee",
                participant_role="visitor",
                invited_by="admin"
            )
            db.add(participant)
            created_participants.append(participant_data["full_name"])
        else:
            # Update existing participant with international travel info
            existing.travelling_from_country = participant_data["travelling_from_country"]
            existing.status = participant_data["status"]
            created_participants.append(f"{participant_data['full_name']} (updated)")
    
    db.commit()
    
    return {
        "message": f"Created/updated {len(created_participants)} test international visitors",
        "participants": created_participants,
        "event": event.title
    }

@router.delete("/clear-test-data")
async def clear_test_data(
    tenant_context: str,
    current_user = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Clear test international visitors"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get events for this tenant
    events = db.query(Event).filter(Event.tenant_id == tenant.id).all()
    event_ids = [event.id for event in events]
    
    # Delete test participants
    test_emails = [
        "john.kamau@msf.org",
        "sarah.mwangi@msf.org", 
        "ahmed.hassan@msf.org",
        "grace.nyong@msf.org",
        "mohamed.ali@msf.org"
    ]
    
    deleted_count = 0
    for email in test_emails:
        participants = db.query(EventParticipant).filter(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.email == email
        ).all()
        
        for participant in participants:
            db.delete(participant)
            deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Deleted {deleted_count} test participants"
    }