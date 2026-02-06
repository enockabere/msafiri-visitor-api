"""
Certificate generation endpoints for events.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.event_certificate import ParticipantCertificate, EventCertificate
from app.models.certificate_template import CertificateTemplate
import logging
from typing import Optional
from datetime import datetime
import cloudinary
import cloudinary.uploader
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, red
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os

logger = logging.getLogger(__name__)

router = APIRouter()

def generate_certificate_pdf(participant: EventParticipant, event: Event, template_variables: dict) -> bytes:
    """Generate certificate PDF content."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=red
    )
    
    content = []
    
    # Certificate Title
    content.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    content.append(Spacer(1, 20))
    
    # Participant name
    participant_name = participant.certificate_name or participant.full_name
    name_style = ParagraphStyle(
        'ParticipantName',
        parent=styles['Normal'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=black
    )
    content.append(Paragraph(f"This is to certify that", styles['Normal']))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>{participant_name}</b>", name_style))
    content.append(Spacer(1, 20))
    
    # Event details
    content.append(Paragraph(f"has successfully completed", styles['Normal']))
    content.append(Spacer(1, 10))
    content.append(Paragraph(f"<b>{event.title}</b>", styles['Heading2']))
    content.append(Spacer(1, 10))
    
    if template_variables.get('courseDescription'):
        content.append(Paragraph(template_variables['courseDescription'], styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Event details
    content.append(Paragraph(f"Event Location: {event.location}", styles['Normal']))
    content.append(Paragraph(f"Event Date: {event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}", styles['Normal']))
    content.append(Spacer(1, 30))
    
    # Signatures
    if template_variables.get('organizerName'):
        content.append(Paragraph(f"Organizer: {template_variables['organizerName']}", styles['Normal']))
        if template_variables.get('organizerTitle'):
            content.append(Paragraph(f"Title: {template_variables['organizerTitle']}", styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Certificate date
    cert_date = template_variables.get('certificateDate', datetime.now().strftime('%Y-%m-%d'))
    content.append(Paragraph(f"Date Issued: {cert_date}", styles['Normal']))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()

@router.get("/events/{event_id}/participant/{participant_id}/certificate/generate")
async def generate_certificate(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate certificate for participant."""
    try:
        logger.info(f"📜 CERT GEN: Generating certificate for event {event_id}, participant {participant_id}")
        
        # Get event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get participant
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id,
            EventParticipant.event_id == event_id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get participant certificate
        participant_cert = db.query(ParticipantCertificate).filter(
            ParticipantCertificate.participant_id == participant_id
        ).first()
        
        if not participant_cert:
            raise HTTPException(status_code=404, detail="Certificate not assigned to participant")
        
        # Get event certificate and template
        event_cert = db.query(EventCertificate).filter(
            EventCertificate.id == participant_cert.event_certificate_id
        ).first()
        
        if not event_cert:
            raise HTTPException(status_code=404, detail="Event certificate not found")
        
        # Get template variables (stored in event_certificates table)
        template_variables = event_cert.template_variables or {}
        
        # Generate PDF
        pdf_content = generate_certificate_pdf(participant, event, template_variables)
        
        # Return PDF
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=certificate-{event.title.replace(' ', '-')}-{participant.full_name.replace(' ', '-')}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"📜 CERT GEN ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{event_id}/participant/{participant_id}/certificate/download")
async def download_certificate(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Download certificate for participant."""
    try:
        # Same logic as generate but with download header
        response = await generate_certificate(event_id, participant_id, db)
        
        # Change header to force download
        response.headers["Content-Disposition"] = response.headers["Content-Disposition"].replace("inline", "attachment")
        
        return response
        
    except Exception as e:
        logger.error(f"📜 CERT DOWNLOAD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
