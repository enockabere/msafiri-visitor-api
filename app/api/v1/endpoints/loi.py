from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.passport_record import PassportRecord
from app.models.event_participant import EventParticipant
from app.models.invitation_template import InvitationTemplate
import requests
import os

router = APIRouter()

@router.get("/participant/{participant_email}/event/{event_id}/loi")
async def get_participant_loi(
    participant_email: str,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get LOI data for a participant by email and event ID"""
    
    # First, verify the participant exists for this event
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == participant_email,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found for this event"
        )
    
    # Get the passport record (which contains the record_id for LOI)
    passport_record = db.query(PassportRecord).filter(
        PassportRecord.user_email == participant_email,
        PassportRecord.event_id == event_id
    ).first()
    
    if not passport_record:
        raise HTTPException(
            status_code=404,
            detail="No LOI record found for this participant"
        )
    
    # Fetch LOI data from external API using the record_id
    try:
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{passport_record.record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        payload = {"passport_id": passport_record.record_id}
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract data from JSON-RPC response structure
            if response_data.get('result', {}).get('status') == 'success':
                loi_data = response_data['result']['data']
                return {
                    "participant_email": participant_email,
                    "participant_name": participant.full_name,
                    "event_id": event_id,
                    "record_id": passport_record.record_id,
                    "loi_data": loi_data
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch LOI data from external API"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch LOI data from external API: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.get("/record/{record_id}/loi")
async def get_loi_by_record_id(record_id: int):
    """Get LOI data directly by record ID (for public access)"""
    
    try:
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        payload = {"passport_id": record_id}
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract data from JSON-RPC response structure
            if response_data.get('result', {}).get('status') == 'success':
                return response_data['result']['data']
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch LOI data from external API"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch LOI data: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.get("/slug/{slug}")
async def get_loi_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get LOI data by slug (for public access with hidden record IDs)"""
    
    # Find the passport record by slug
    passport_record = db.query(PassportRecord).filter(
        PassportRecord.slug == slug
    ).first()
    
    if not passport_record:
        raise HTTPException(
            status_code=404,
            detail="LOI document not found"
        )
    
    try:
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{passport_record.record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        payload = {"passport_id": passport_record.record_id}
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract data from JSON-RPC response structure
            if response_data.get('result', {}).get('status') == 'success':
                return response_data['result']['data']
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to fetch LOI data from external API"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch LOI data: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.get("/participant/{participant_email}/event/{event_id}/check")
async def check_loi_availability(
    participant_email: str,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Check if LOI is available for a participant"""
    
    # First, verify the participant exists for this event
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == participant_email,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        return {
            "available": False,
            "message": "Participant not found for this event"
        }
    
    # Get the passport record
    passport_record = db.query(PassportRecord).filter(
        PassportRecord.user_email == participant_email,
        PassportRecord.event_id == event_id
    ).first()
    
    if not passport_record:
        return {
            "available": False,
            "message": "No LOI record found for this participant"
        }
    
    # Generate slug if it doesn't exist
    if not passport_record.slug:
        passport_record.generate_slug()
        db.commit()
    
    return {
        "available": True,
        "slug": passport_record.slug,
        "message": "LOI document is available"
    }

@router.post("/generate-slugs")
async def generate_slugs_for_existing_records(db: Session = Depends(get_db)):
    """Generate slugs for all passport records that don't have one (admin utility)"""
    
    try:
        # Get all passport records without slugs
        records_without_slugs = db.query(PassportRecord).filter(
            PassportRecord.slug.is_(None)
        ).all()
        
        updated_count = 0
        for record in records_without_slugs:
            try:
                record.generate_slug()
                updated_count += 1
            except Exception as e:
                print(f"Error generating slug for record ID {record.id}: {e}")
        
        db.commit()
        
        return {
            "message": f"Successfully generated slugs for {updated_count} records",
            "total_records_processed": len(records_without_slugs),
            "successful_updates": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate slugs: {str(e)}"
        )

# Add the missing generation endpoint that the frontend is calling
@router.get("/events/{event_id}/participant/{participant_id}/download")
async def download_loi_pdf(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate downloadable LOI PDF with QR code"""
    from fastapi.responses import Response
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    import requests as req
    
    # Get the active invitation template
    template = db.query(InvitationTemplate).filter(
        InvitationTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="No active invitation template found"
        )
    
    # Get the participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found"
        )
    
    try:
        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, "Letter of Invitation")
        
        # Add participant info
        p.setFont("Helvetica", 12)
        y_position = height - 100
        p.drawString(50, y_position, f"Participant: {participant.full_name}")
        y_position -= 30
        
        # Get event details
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            p.drawString(50, y_position, f"Event: {event.title}")
            y_position -= 20
            if event.start_date and event.end_date:
                p.drawString(50, y_position, f"Dates: {event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}")
                y_position -= 20
            if event.location:
                p.drawString(50, y_position, f"Location: {event.location}")
                y_position -= 40
        
        # Add QR code
        try:
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000/portal')
            web_url = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/loi/events/{event_id}/participant/{participant_id}/generate"
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={web_url}"
            
            # Fetch QR code image
            qr_response = req.get(qr_url, timeout=10)
            if qr_response.status_code == 200:
                qr_image = ImageReader(io.BytesIO(qr_response.content))
                p.drawImage(qr_image, width - 200, y_position - 150, width=150, height=150)
                
                # Add QR code label
                p.setFont("Helvetica", 10)
                p.drawString(width - 200, y_position - 170, "Scan to view online")
        except Exception as e:
            print(f"Error adding QR code: {e}")
        
        # Add note about template
        p.setFont("Helvetica", 10)
        p.drawString(50, 50, "This document was generated from the active invitation template.")
        p.drawString(50, 35, "For the complete formatted version, scan the QR code above.")
        
        p.showPage()
        p.save()
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return PDF as download
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=LOI_{participant.full_name.replace(' ', '_')}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )

@router.get("/events/{event_id}/participant/{participant_id}/generate")
async def generate_loi_for_participant(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate LOI using active template for a participant"""
    from fastapi.responses import HTMLResponse
    import re
    from datetime import datetime
    
    # Get the active invitation template for the tenant
    template = db.query(InvitationTemplate).filter(
        InvitationTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="No active invitation template found"
        )
    
    # Get the participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found"
        )
    
    # Get event details
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == event_id).first()
    
    # Get passport data from external API if available
    passport_data = {}
    try:
        passport_record = db.query(PassportRecord).filter(
            PassportRecord.user_email == participant.email,
            PassportRecord.event_id == event_id
        ).first()
        
        if passport_record:
            API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{passport_record.record_id}"
            API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
            
            headers = {
                'x-api-key': API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            
            payload = {"passport_id": passport_record.record_id}
            response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('result', {}).get('status') == 'success':
                    passport_data = response_data['result']['data']
    except Exception as e:
        print(f"Warning: Could not fetch passport data: {e}")
    
    try:
        # Start with template HTML
        html_content = template.template_content or ''
        
        # Ensure proper HTML structure
        if not html_content.strip().startswith('<!DOCTYPE html>') and not html_content.strip().startswith('<html'):
            html_content = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Letter of Invitation</title>
</head>
<body>
{html_content}
</body>
</html>'''
        
        # Prepare template variables
        event_name = event.title if event else f"Event {event_id}"
        event_dates = f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else "TBD"
        event_location = event.location if event else "TBD"
        
        # Use passport data if available, otherwise use participant data
        passport_number = passport_data.get('passport_number') or getattr(participant, 'passport_number', None) or 'N/A'
        nationality = passport_data.get('nationality') or getattr(participant, 'nationality', None) or 'N/A'
        date_of_birth = passport_data.get('date_of_birth') or getattr(participant, 'date_of_birth', None) or 'N/A'
        
        variables = {
            'participant_name': participant.full_name,
            'event_name': event_name,
            'event_dates': event_dates,
            'event_location': event_location,
            'organization_name': 'MSF',
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'passport_number': passport_number,
            'nationality': nationality,
            'date_of_birth': str(date_of_birth),
            'event_start_date': event.start_date.strftime('%Y-%m-%d') if event and event.start_date else 'TBD',
            'event_end_date': event.end_date.strftime('%Y-%m-%d') if event and event.end_date else 'TBD',
        }
        
        # Replace template variables
        for key, value in variables.items():
            pattern = f'{{{{\\s*{key}\\s*}}}}'
            html_content = re.sub(pattern, str(value), html_content, flags=re.IGNORECASE)
        
        # Add logo if available
        if template.logo_url:
            logo_html = f'<img src="{template.logo_url}" alt="Logo" style="max-width: 200px; height: auto;" />'
            html_content = html_content.replace('{{logo}}', logo_html)
        else:
            html_content = html_content.replace('{{logo}}', '')
        
        # Add signature if available
        if template.signature_url:
            signature_html = f'<img src="{template.signature_url}" alt="Signature" style="max-width: 120px; max-height: 60px; height: auto;" />'
            html_content = html_content.replace('{{signature}}', signature_html)
        else:
            html_content = html_content.replace('{{signature}}', '')
        
        # Add address fields
        if template.address_fields:
            address_text = '<br>'.join(template.address_fields) if isinstance(template.address_fields, list) else str(template.address_fields).replace('\n', '<br>')
            html_content = html_content.replace('{{organization_address}}', address_text)
        else:
            html_content = html_content.replace('{{organization_address}}', 'MSF Kenya, Nairobi')
        
        # Add signature footer
        if template.signature_footer_fields:
            footer_text = '<br>'.join(template.signature_footer_fields) if isinstance(template.signature_footer_fields, list) else str(template.signature_footer_fields).replace('\n', '<br>')
            html_content = html_content.replace('{{signature_footer}}', footer_text)
        else:
            html_content = html_content.replace('{{signature_footer}}', '')
        
        # Generate QR code if enabled
        if template.enable_qr_code:
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000/portal')
            public_url = f"{frontend_url}/public/loi/{participant_id}-{event_id}"
            qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={public_url}"
            qr_code_html = f'''
            <div style="text-align: center; margin: 10px 0;">
                <img src="{qr_code_url}" alt="QR Code" style="width: 100px; height: 100px;" />
                <div style="font-size: 10px; margin-top: 5px; color: #666;">Scan to verify document</div>
            </div>
            '''
            html_content = html_content.replace('{{qr_code}}', qr_code_html)
        else:
            html_content = html_content.replace('{{qr_code}}', '')
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LOI: {str(e)}"
        )

@router.get("/events/{event_id}/participant/{participant_id}/data")
async def get_loi_data_for_participant(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Get LOI data for mobile app (replaces external API base64)"""
    
    # Get the participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found"
        )
    
    # Get event details
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == event_id).first()
    
    # Get passport data from external API if available
    passport_data = {}
    try:
        passport_record = db.query(PassportRecord).filter(
            PassportRecord.user_email == participant.email,
            PassportRecord.event_id == event_id
        ).first()
        
        if passport_record:
            API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{passport_record.record_id}"
            API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
            
            headers = {
                'x-api-key': API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            
            payload = {"passport_id": passport_record.record_id}
            response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('result', {}).get('status') == 'success':
                    passport_data = response_data['result']['data']
    except Exception as e:
        print(f"Warning: Could not fetch passport data: {e}")
    
    # Return structured data instead of base64
    return {
        "participant_name": participant.full_name,
        "participant_email": participant.email,
        "event_name": event.title if event else f"Event {event_id}",
        "event_dates": f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else "TBD",
        "event_location": event.location if event else "TBD",
        "passport_number": passport_data.get('passport_number') or getattr(participant, 'passport_number', None) or 'N/A',
        "nationality": passport_data.get('nationality') or getattr(participant, 'nationality', None) or 'N/A',
        "date_of_birth": passport_data.get('date_of_birth') or getattr(participant, 'date_of_birth', None) or 'N/A',
        "loi_url": f"/v1/loi/events/{event_id}/participant/{participant_id}/generate",
        "has_template": True
    }