"""
Bulk Badge Generation Endpoint

Generates multiple badges in a single PDF for printing.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.database import get_db
from app.models.event_badge import EventBadge
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.services.badge_generation import replace_template_variables
from io import BytesIO
import os

router = APIRouter()


class BulkBadgeRequest(BaseModel):
    participant_ids: List[int]
    event_id: int


@router.post("/events/{event_id}/badges/bulk-print")
async def generate_bulk_badges(
    event_id: int,
    request: BulkBadgeRequest,
    db: Session = Depends(get_db),
    x_tenant_id: str = Header(None)
):
    """Generate multiple badges in a single PDF for printing"""
    from app.services.badge_generation import generate_badge
    from PyPDF2 import PdfMerger
    import tempfile
    
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get badge template
    from sqlalchemy import text
    badge_query = text("""
        SELECT 
            eb.id as event_badge_id,
            bt.template_content,
            bt.logo_url,
            eb.template_variables
        FROM event_badges eb
        JOIN badge_templates bt ON eb.badge_template_id = bt.id
        WHERE eb.event_id = :event_id
        AND bt.is_active = true
        LIMIT 1
    """)
    
    badge_result = db.execute(badge_query, {"event_id": event_id}).fetchone()
    if not badge_result:
        raise HTTPException(status_code=404, detail="No badge template assigned to this event")
    
    # Get participants
    participants = db.query(EventParticipant).filter(
        EventParticipant.id.in_(request.participant_ids),
        EventParticipant.event_id == event_id
    ).all()
    
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")
    
    # Get tagline
    template_vars = badge_result.template_variables or {}
    tagline = template_vars.get('tagline', '') or template_vars.get('badgeTagline', '')
    
    # Generate individual badge PDFs
    merger = PdfMerger()
    
    for participant in participants:
        try:
            badge_url = await generate_badge(
                participant_id=participant.id,
                event_id=event_id,
                template_html=badge_result.template_content,
                participant_name=participant.full_name,
                badge_name=participant.badge_name or participant.full_name,
                event_name=event.title,
                event_dates=f"{event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}",
                start_date=event.start_date.strftime('%B %d, %Y'),
                end_date=event.end_date.strftime('%B %d, %Y'),
                tagline=tagline,
                participant_role=participant.role or 'Participant',
                logo_url=badge_result.logo_url
            )
            
            # Download the badge PDF and add to merger
            import requests
            response = requests.get(badge_url)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(response.content)
                    tmp.flush()
                    merger.append(tmp.name)
        except Exception as e:
            print(f"Error generating badge for {participant.full_name}: {e}")
            continue
    
    # Write merged PDF
    output = BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bulk-badges-event-{event_id}.pdf"
        }
    )
