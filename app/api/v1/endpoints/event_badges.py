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
from app.services.badge_generation import generate_badge
from sqlalchemy import text
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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

@router.put("/{event_id}/badges/{badge_id}", response_model=EventBadgeResponse)
def update_event_badge(
    event_id: int,
    badge_id: int,
    badge_data: EventBadgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_slug: str = Depends(get_tenant_context)
):
    """Update an event badge"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get existing badge
    badge = db.query(EventBadge).filter(
        EventBadge.id == badge_id,
        EventBadge.event_id == event_id,
        EventBadge.tenant_id == tenant.id
    ).first()
    
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    # Update badge template if provided
    if badge_data.badge_template_id:
        template = db.query(BadgeTemplate).filter(
            BadgeTemplate.id == badge_data.badge_template_id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Badge template not found")
        badge.badge_template_id = badge_data.badge_template_id
    
    # Update template variables
    if badge_data.template_variables is not None:
        badge.template_variables = badge_data.template_variables
    
    badge.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(badge)
    
    return badge

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

@router.get("/{event_id}/participant/{participant_id}/badge/generate")
async def generate_participant_badge(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate badge for a specific participant"""
    try:
        # Get participant and event info
        participant_query = text("""
            SELECT 
                ep.id,
                ep.full_name,
                ep.certificate_name,
                ep.badge_name,
                ep.email,
                e.title as event_name,
                e.start_date,
                e.end_date,
                e.location as event_location
            FROM event_participants ep
            JOIN events e ON ep.event_id = e.id
            WHERE ep.id = :participant_id
            AND ep.event_id = :event_id
        """)
        
        participant = db.execute(participant_query, {
            "participant_id": participant_id,
            "event_id": event_id
        }).fetchone()
        
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get event badge configuration with template content
        badge_config_query = text("""
            SELECT 
                eb.id,
                eb.template_variables,
                bt.template_content,
                bt.name as template_name
            FROM event_badges eb
            JOIN badge_templates bt ON eb.badge_template_id = bt.id
            WHERE eb.event_id = :event_id
            LIMIT 1
        """)
        
        badge_config = db.execute(badge_config_query, {
            "event_id": event_id
        }).fetchone()
        
        if not badge_config:
            raise HTTPException(status_code=404, detail="No badge template configured for this event")
        
        # Get tagline from event badge template variables (not badge template)
        template_vars = badge_config.template_variables or {}
        tagline = template_vars.get('tagline', '') or template_vars.get('badgeTagline', '')
        
        logger.info(f"Badge config template_variables: {template_vars}")
        logger.info(f"Extracted tagline: '{tagline}'")
        logger.info(f"Template content preview: {badge_config.template_content[:200]}...")
        
        # Format event dates
        start_date_formatted = participant.start_date.strftime('%B %d, %Y')
        end_date_formatted = participant.end_date.strftime('%B %d, %Y')
        event_dates = f"{start_date_formatted} - {end_date_formatted}"
        
        # Use badge_name if available, otherwise use certificate_name, otherwise use full_name
        badge_name = participant.badge_name or participant.certificate_name or participant.full_name
        
        # Generate badge PDF with template content that already has images
        badge_url = await generate_badge(
            participant_id=participant.id,
            event_id=event_id,
            template_html=badge_config.template_content,
            participant_name=participant.full_name,
            badge_name=badge_name,
            event_name=participant.event_name,
            event_dates=event_dates,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            tagline=tagline,
            participant_role="Participant"
        )
        
        # Save badge record
        existing_badge_query = text("""
            SELECT id FROM participant_badges 
            WHERE event_badge_id = :badge_id 
            AND participant_id = :participant_id
        """)
        
        existing_badge = db.execute(existing_badge_query, {
            "badge_id": badge_config.id,
            "participant_id": participant.id
        }).fetchone()
        
        if existing_badge:
            db.execute(text("""
                UPDATE participant_badges 
                SET badge_url = :badge_url, issued_at = :issued_at
                WHERE id = :badge_id
            """), {
                "badge_url": badge_url,
                "issued_at": datetime.utcnow(),
                "badge_id": existing_badge.id
            })
        else:
            db.execute(text("""
                INSERT INTO participant_badges 
                (event_badge_id, participant_id, badge_url, issued_at)
                VALUES (:badge_id, :participant_id, :badge_url, :issued_at)
            """), {
                "badge_id": badge_config.id,
                "participant_id": participant.id,
                "badge_url": badge_url,
                "issued_at": datetime.utcnow()
            })
        
        db.commit()
        
        # Return the generated badge URL for viewing
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=badge_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error generating badge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate badge: {str(e)}")