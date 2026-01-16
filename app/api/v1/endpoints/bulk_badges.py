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
    """Generate multiple badges in a single PDF with 2 badges per page"""
    from weasyprint import HTML, CSS
    
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
    
    # Build combined HTML with 2 badges per page
    badges_html = []
    for participant in participants:
        template_data = {
            'participant_name': participant.full_name,
            'badge_name': participant.badge_name or participant.full_name,
            'event_name': event.title,
            'event_dates': f"{event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}",
            'start_date': event.start_date.strftime('%B %d, %Y'),
            'end_date': event.end_date.strftime('%B %d, %Y'),
            'tagline': tagline,
            'participant_role': participant.role or 'Participant',
            'logo': badge_result.logo_url or '',
            'qr_code': f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/events/{event_id}/participant/{participant.id}/badge/generate"
        }
        badge_html = replace_template_variables(badge_result.template_content, template_data)
        badges_html.append(f'<div class="badge-container">{badge_html}</div>')
    
    # Combine all badges with grid layout
    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: A4 landscape;
                margin: 0;
            }}
            body {{
                margin: 0;
                padding: 0;
            }}
            .badge-container {{
                width: 50%;
                height: 100vh;
                float: left;
                page-break-inside: avoid;
            }}
            .badge-container:nth-child(2n+1) {{
                page-break-after: avoid;
            }}
            .badge-container:nth-child(2n) {{
                page-break-after: always;
            }}
            .badge-container:last-child {{
                page-break-after: auto;
            }}
        </style>
    </head>
    <body>
        {''.join(badges_html)}
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_bytes = HTML(string=combined_html).write_pdf()
    
    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bulk-badges-event-{event_id}.pdf"
        }
    )
