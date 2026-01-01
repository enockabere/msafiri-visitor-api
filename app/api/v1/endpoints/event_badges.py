from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.deps import get_current_user, get_tenant_context
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.event_badge import EventBadge, ParticipantBadge
from app.models.badge_template import BadgeTemplate
from app.schemas.event_badge import EventBadgeCreate, EventBadgeUpdate, EventBadgeResponse, ParticipantBadgeResponse

router = APIRouter()

@router.get("/{event_id}/badges", response_model=List[EventBadgeResponse])
def get_event_badges(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all badges for an event"""
    print(f"\n🔍 DEBUG: get_event_badges called with event_id={event_id}")
    print(f"🔍 DEBUG: current_user={current_user.email if current_user else 'None'}")
    
    # Get tenant from request headers
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest
    import inspect
    
    # Try to get tenant from different possible sources
    tenant_slug = None
    
    # Check if we can get it from the request context
    try:
        from fastapi import Request
        # This is a workaround - in a real scenario you'd inject Request as a dependency
        # For now, let's try to get tenant from the event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            print(f"🔍 DEBUG: Event {event_id} not found")
            raise HTTPException(status_code=404, detail="Event not found")
        
        tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first()
        if not tenant:
            print(f"🔍 DEBUG: Tenant for event {event_id} not found")
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        print(f"🔍 DEBUG: Found tenant: {tenant.slug}")
        
    except Exception as e:
        print(f"🔍 DEBUG: Error getting tenant: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting tenant: {str(e)}")
    
    # Get badges
    print(f"🔍 DEBUG: Querying badges for event_id={event_id}, tenant_id={tenant.id}")
    badges = db.query(EventBadge).filter(
        EventBadge.event_id == event_id,
        EventBadge.tenant_id == tenant.id
    ).all()
    
    print(f"🔍 DEBUG: Found {len(badges)} badges")
    return badges

@router.post("/{event_id}/badges", response_model=EventBadgeResponse)
def create_event_badge(
    event_id: int,
    badge_data: EventBadgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Create a badge for an event"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Verify event exists and belongs to tenant
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.tenant_id == tenant.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get badge template
    template = db.query(BadgeTemplate).filter(
        BadgeTemplate.id == badge_data.badge_template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Badge template not found")
    
    # Create event badge
    event_badge = EventBadge(
        event_id=event_id,
        badge_template_id=badge_data.badge_template_id,
        template_variables=badge_data.template_variables,
        tenant_id=tenant.id,
        created_by=current_user.id
    )
    
    db.add(event_badge)
    db.commit()
    db.refresh(event_badge)
    
    # Create participant badges for all event participants
    participants = db.query(EventParticipant).filter(EventParticipant.event_id == event_id).all()
    
    for participant in participants:
        participant_badge = ParticipantBadge(
            event_badge_id=event_badge.id,
            participant_id=participant.id
        )
        db.add(participant_badge)
    
    db.commit()
    
    return event_badge

@router.delete("/{event_id}/badges/{badge_id}")
def delete_event_badge(
    event_id: int,
    badge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Delete an event badge"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    badge = db.query(EventBadge).filter(
        EventBadge.id == badge_id,
        EventBadge.event_id == event_id,
        EventBadge.tenant_id == tenant.id
    ).first()
    
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    # Delete associated participant badges
    db.query(ParticipantBadge).filter(
        ParticipantBadge.event_badge_id == badge_id
    ).delete()
    
    db.delete(badge)
    db.commit()
    return {"message": "Badge deleted successfully"}