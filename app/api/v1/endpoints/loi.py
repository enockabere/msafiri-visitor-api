from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.passport_record import PassportRecord
from app.models.event_participant import EventParticipant
from app.models.invitation_template import InvitationTemplate
import requests
import os
import logging

logger = logging.getLogger(__name__)

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
    """Download LOI PDF - same as generate but with download header"""
    # Use the same generation logic but redirect to download
    response = await generate_loi_pdf(event_id, participant_id, db)
    return response

@router.get("/events/{event_id}/participant/{participant_id}/generate")
async def generate_loi_pdf(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate LOI PDF and upload to Cloudinary for mobile app access - PUBLIC ENDPOINT"""
    from fastapi.responses import RedirectResponse
    from app.services.loi_generation import generate_loi_document
    from app.models.invitation_template import InvitationTemplate
    from app.models.event import Event
    import re
    from datetime import datetime
    
    try:
        logger.info(f"Generating LOI PDF for event {event_id}, participant {participant_id}")
        
        # Get the event's assigned invitation template
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )
        
        if not event.invitation_template_id:
            raise HTTPException(
                status_code=404,
                detail="No invitation template assigned to this event"
            )
        
        template = db.query(InvitationTemplate).filter(
            InvitationTemplate.id == event.invitation_template_id
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Invitation template not found"
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
        # event already fetched above
        
        # Get passport data from external API if available
        passport_data = {}
        passport_record = None
        try:
            passport_record = db.query(PassportRecord).filter(
                PassportRecord.user_email == participant.email,
                PassportRecord.event_id == event_id
            ).first()
            
            if not passport_record:
                raise HTTPException(
                    status_code=404,
                    detail="No passport data found. Please upload passport details first."
                )
            
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
                    logger.info(f"Passport data fetched successfully")
                else:
                    logger.warning(f"External API returned unsuccessful status")
                    raise HTTPException(
                        status_code=400,
                        detail="Could not retrieve passport data from external system"
                    )
            else:
                logger.warning(f"External API returned status {response.status_code}")
                raise HTTPException(
                    status_code=400,
                    detail="Could not retrieve passport data from external system"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching passport data: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Could not retrieve passport data. Please ensure passport details are uploaded."
            )
        
        # Prepare event details
        event_name = event.title if event else f"Event {event_id}"
        event_start_date = event.start_date.strftime('%B %d, %Y') if event and event.start_date else "TBD"
        event_end_date = event.end_date.strftime('%B %d, %Y') if event and event.end_date else "TBD"
        event_dates = f"{event.start_date.strftime('%B %d')} - {event.end_date.strftime('%B %d, %Y')}" if event and event.start_date and event.end_date else "TBD"
        event_location = event.location if event else "TBD"
        
        # Use passport data - all fields are required
        passport_number = passport_data.get('passport_no')
        nationality = passport_data.get('nationality')
        date_of_birth = passport_data.get('date_of_birth')
        passport_issue_date = passport_data.get('date_of_issue')
        passport_expiry_date = passport_data.get('date_of_expiry')
        
        # Validate that we have the essential passport data
        if not passport_number or not nationality:
            raise HTTPException(
                status_code=400,
                detail="Incomplete passport data. Passport number and nationality are required."
            )
        
        # Log what passport data fields we found
        
        # Get accommodation details from location_id if available
        accommodation_details = 'N/A'
        if passport_data.get('location_id', {}).get('accommodation'):
            accommodation_details = passport_data['location_id']['accommodation']
        elif event and event.location:
            accommodation_details = event.location
        

        
        # Prepare enhanced template HTML with logos, signatures, and proper styling
        template_html = template.template_content or ''
        
        # Ensure proper HTML structure with responsive CSS
        if not template_html.strip().startswith('<!DOCTYPE html>') and not template_html.strip().startswith('<html'):
            template_html = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Letter of Invitation</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .logo {{ max-width: 200px; height: auto; }}
    .signature {{ max-width: 120px; max-height: 60px; height: auto; }}
    .qr-code {{ max-width: 150px; height: auto; }}
    @media print {{ body {{ margin: 0; }} }}
  </style>
</head>
<body>
{template_html}
</body>
</html>'''
        
        # Add logo if available
        if hasattr(template, 'logo_url') and template.logo_url:
            logo_html = f'<img src="{template.logo_url}" alt="Logo" class="logo" />'
            template_html = template_html.replace('{{logo}}', logo_html)
        else:
            template_html = template_html.replace('{{logo}}', '')
        
        # Add signature if available
        if hasattr(template, 'signature_url') and template.signature_url:
            signature_html = f'<img src="{template.signature_url}" alt="Signature" class="signature" />'
            template_html = template_html.replace('{{signature}}', signature_html)
        else:
            template_html = template_html.replace('{{signature}}', '')
        
        # Add address fields
        if hasattr(template, 'address_fields') and template.address_fields:
            address_lines = []
            fields = template.address_fields if isinstance(template.address_fields, list) else []
            
            for field in fields:
                text = ''
                field_type = 'text'
                
                if isinstance(field, dict):
                    text = field.get('text', '')
                    field_type = field.get('type', 'text')
                elif isinstance(field, str):
                    text = field
                    # Auto-detect type from content
                    if text.startswith('http://') or text.startswith('https://') or text.startswith('www.'):
                        field_type = 'link'
                    elif '@' in text and '.' in text and ' ' not in text:
                        field_type = 'email'
                    elif text.startswith('Tel:') or text.startswith('+'):
                        field_type = 'phone'
                
                if field_type == 'link':
                    address_lines.append(f'<a href="{text}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                elif field_type == 'email':
                    address_lines.append(f'<a href="mailto:{text}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                elif field_type == 'phone':
                    phone_href = text.replace('Tel:', '').strip() if text.startswith('Tel:') else text
                    address_lines.append(f'<a href="tel:{phone_href}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                else:
                    address_lines.append(f'<p>{text}</p>')
            
            address_html = ''.join(address_lines)
            template_html = template_html.replace('{{organizationAddress}}', address_html)
            template_html = template_html.replace('{{organization_address}}', address_html)
        else:
            template_html = template_html.replace('{{organizationAddress}}', '<p>MSF Kenya, Nairobi</p>')
            template_html = template_html.replace('{{organization_address}}', '<p>MSF Kenya, Nairobi</p>')
        
        # Add signature footer
        if hasattr(template, 'signature_footer_fields') and template.signature_footer_fields:
            footer_lines = []
            fields = template.signature_footer_fields if isinstance(template.signature_footer_fields, list) else []
            
            for field in fields:
                if isinstance(field, dict):
                    text = field.get('text', '')
                    field_type = field.get('type', 'text')
                    
                    if field_type == 'link':
                        footer_lines.append(f'<a href="{text}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                    elif field_type == 'email':
                        footer_lines.append(f'<a href="mailto:{text}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                    elif field_type == 'phone':
                        footer_lines.append(f'<a href="tel:{text}" style="color: #1a73e8; text-decoration: underline;">{text}</a>')
                    else:
                        footer_lines.append(text)
                elif isinstance(field, str):
                    footer_lines.append(field)
            
            footer_html = '<br>'.join(footer_lines)
            template_html = template_html.replace('{{signatureFooter}}', footer_html)
            template_html = template_html.replace('{{signature_footer}}', footer_html)
        else:
            template_html = template_html.replace('{{signatureFooter}}', '')
            template_html = template_html.replace('{{signature_footer}}', '')
        
        # Generate LOI PDF and upload to Cloudinary with all data
        pdf_url, loi_slug = await generate_loi_document(
            participant_id=participant_id,
            event_id=event_id,
            template_html=template_html,  # Use enhanced template with logos/signatures
            participant_name=participant.full_name,
            passport_number=passport_number,
            nationality=nationality,
            date_of_birth=str(date_of_birth),
            passport_issue_date=str(passport_issue_date),
            passport_expiry_date=str(passport_expiry_date),
            event_name=event_name,
            event_dates=event_dates,
            event_location=event_location,
            organization_name='MSF'
        )
        
        logger.info(f"PDF generated and uploaded: {pdf_url}")
        
        # Return redirect to Cloudinary PDF URL for direct viewing
        return RedirectResponse(url=pdf_url, status_code=302)
        
    except Exception as e:
        logger.error(f"LOI generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/template")
async def debug_template(db: Session = Depends(get_db)):
    """Debug endpoint to check current invitation template"""
    template = db.query(InvitationTemplate).filter(
        InvitationTemplate.is_active == True
    ).first()
    
    if not template:
        return {"error": "No active template found"}
    
    return {
        "template_id": template.id,
        "template_name": getattr(template, 'name', 'Unknown'),
        "template_content_length": len(template.template_content or ''),
        "template_preview": (template.template_content or '')[:500] + "..." if len(template.template_content or '') > 500 else template.template_content,
        "is_active": template.is_active
    }

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
        "passport_number": passport_data.get('passport_no') or getattr(participant, 'passport_number', None) or 'N/A',
        "nationality": passport_data.get('nationality') or getattr(participant, 'nationality', None) or 'N/A',
        "date_of_birth": passport_data.get('date_of_birth') or getattr(participant, 'date_of_birth', None) or 'N/A',
        "loi_url": f"/v1/loi/events/{event_id}/participant/{participant_id}/generate",
        "has_template": True
    }