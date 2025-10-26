from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api import deps
from app.core.permissions import has_accommodation_permissions
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.tenant import Tenant
from typing import List, Dict

router = APIRouter()

@router.get("/confirmed-guests")
async def get_confirmed_guests(
    tenant_context: str,
    current_user = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all confirmed guests from all events for guest house booking"""
    
    # Check permissions
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get confirmed participants from events within 1 month after end date
    from datetime import datetime, timedelta
    one_month_ago = datetime.now() - timedelta(days=30)
    
    confirmed_guests = db.query(
        EventParticipant.full_name,
        EventParticipant.email,
        Event.title.label("event_title")
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        Event.tenant_id == tenant.id,
        EventParticipant.status == "confirmed",
        Event.end_date >= one_month_ago
    ).all()
    
    # Format response
    guests = []
    for guest in confirmed_guests:
        guests.append({
            "name": guest.full_name,
            "email": guest.email,
            "phone": "",  # Phone not available in EventParticipant model
            "event": guest.event_title,
            "display_text": f"{guest.full_name} ({guest.event_title})"
        })
    
    return {"guests": guests}