from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.passport_record import PassportRecord
from app.models.event_participant import EventParticipant
from app.models.invitation_template import InvitationTemplate
from app.services.loi_generation import generate_loi_document
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
@router.get("/events/{event_id}/loi/{template_id}/generate/{participant_id}")
async def generate_loi_from_event_template(
    event_id: int,
    template_id: int,
    participant_id: int,
    db: Session = Depends(get_db)
):
    """Generate LOI PDF from template for a participant (event-based endpoint)"""
    
    # Get the invitation template
    template = db.query(InvitationTemplate).filter(
        InvitationTemplate.id == template_id,
        InvitationTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail="Active invitation template not found"
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
        # Generate LOI document using the service
        pdf_url, loi_slug = await generate_loi_document(
            participant_id=participant.id,
            event_id=participant.event_id,
            template_html=template.template_content,
            participant_name=participant.full_name,
            event_name=f"Event {participant.event_id}",  # You might want to get actual event name
            event_dates="TBD",  # You might want to get actual event dates
            event_location="TBD",  # You might want to get actual event location
            organization_name="MSF"
        )
        
        # Redirect to the generated PDF
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=pdf_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LOI: {str(e)}"
        )