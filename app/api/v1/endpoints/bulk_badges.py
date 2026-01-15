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
    
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get badge template assigned to event via event_badges
    from sqlalchemy import text
    
    badge_query = text("""
        SELECT 
            eb.id as event_badge_id,
            bt.id as template_id,
            bt.template_content,
            bt.logo_url,
            bt.badge_size,
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
    
    # Determine layout based on badge size
    badges_per_page = 4 if badge_result.badge_size == 'standard' else 2
    
    # Generate HTML for all badges
    badge_htmls = []
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    
    # Get tagline from template variables
    template_vars = badge_result.template_variables or {}
    tagline = template_vars.get('tagline', '') or template_vars.get('badgeTagline', '')
    
    for participant in participants:
        # Generate QR code URL
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={base_url}/api/v1/events/{event_id}/participant/{participant.id}/badge/generate"
        
        # Prepare template data
        template_data = {
            'participant_name': participant.full_name,
            'badge_name': participant.badge_name or participant.full_name,
            'event_name': event.title,
            'event_title': event.title,
            'event_dates': f"{event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}",
            'start_date': event.start_date.strftime('%B %d, %Y'),
            'end_date': event.end_date.strftime('%B %d, %Y'),
            'organization_name': 'MSF',
            'participant_role': participant.role or 'Participant',
            'tagline': tagline,
            'badge_tagline': tagline,
            'qr_code': qr_code_url,
            'qrCode': qr_code_url,
            'QR': qr_code_url,
            'logo': badge_result.logo_url if badge_result.logo_url else '',
            'avatar': '',
        }
        
        # Replace variables in template
        personalized_html = replace_template_variables(badge_result.template_content, template_data)
        
        # Replace QR placeholder
        if 'QR' in personalized_html and qr_code_url:
            qr_img = f'<img src="{qr_code_url}" alt="QR Code" style="width:100%;height:100%;padding:8px;background:white;display:block;object-fit:contain" />'
            personalized_html = personalized_html.replace('>QR<', f'>{qr_img}<')
        
        # Remove style tags and page-break styles from the badge HTML
        import re
        # Remove <style> tags and their content
        personalized_html = re.sub(r'<style[^>]*>.*?</style>', '', personalized_html, flags=re.DOTALL)
        # Remove inline page-break styles
        personalized_html = re.sub(r'page-break-[^:;]+:[^;]+;?', '', personalized_html)
        personalized_html = re.sub(r'break-[^:;]+:[^;]+;?', '', personalized_html)
        
        badge_htmls.append(personalized_html)
    
    # Create combined HTML with proper layout
    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bulk Badges</title>
        <style>
            @page {{
                size: A4 portrait;
                margin: 0;
            }}
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }}
            .page {{
                page-break-after: always;
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
            }}
            .page:last-child {{
                page-break-after: avoid;
            }}
            .badge-wrapper {{
                flex: 1;
                width: 100%;
                height: 50%;
                overflow: hidden;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .badge-wrapper > * {{
                transform: rotate(90deg);
                transform-origin: center center;
            }}
            /* Remove all page breaks from badge content */
            .badge-wrapper, .badge-wrapper * {{
                page-break-before: avoid !important;
                page-break-after: avoid !important;
                page-break-inside: avoid !important;
                break-before: avoid !important;
                break-after: avoid !important;
                break-inside: avoid !important;
            }}
        </style>
    </head>
    <body>
    """
    
    # Group badges into pages
    for i in range(0, len(badge_htmls), badges_per_page):
        page_badges = badge_htmls[i:i + badges_per_page]
        combined_html += '<div class="page">'
        for badge_html in page_badges:
            # Include the full badge HTML with its styles
            combined_html += f'<div class="badge-wrapper">{badge_html}</div>'
        combined_html += '</div>'
    
    combined_html += """
    </body>
    </html>
    """
    
    # Convert to PDF
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=combined_html).write_pdf()
        
        # Return PDF
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=bulk-badges-event-{event_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
