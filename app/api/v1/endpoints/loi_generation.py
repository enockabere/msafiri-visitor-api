"""
LOI Generation Endpoints for Events

Generate LOI documents when configured in portal event management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Any
import logging

from app.db.database import get_db
from app.api import deps
from app.models.user import UserRole
from app.services.loi_generation import generate_loi_document

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/events/{event_id}/loi/generate-all")
async def generate_loi_for_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Generate LOI documents for all participants who have passport data.
    Called when LOI is configured in portal event management.
    """
    
    # Check admin permission
    admin_roles = [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate LOI documents"
        )
    
    # Get event details
    event_query = text("""
        SELECT 
            e.id,
            e.title as event_name,
            e.start_date,
            e.end_date,
            e.location as event_location
        FROM events e
        WHERE e.id = :event_id
    """)
    
    event = db.execute(event_query, {"event_id": event_id}).fetchone()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get event's assigned invitation template
    template_query = text("""
        SELECT 
            it.id,
            it.template_content,
            it.name as template_name
        FROM invitation_templates it
        JOIN events e ON e.invitation_template_id = it.id
        WHERE e.id = :event_id
    """)
    
    template = db.execute(template_query, {"event_id": event_id}).fetchone()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No invitation template assigned to this event. Please assign a template in the LOI tab."
        )
    
    # Get participants who have passport records
    participants_query = text("""
        SELECT DISTINCT
            ep.id,
            ep.full_name,
            ep.email,
            pr.record_id
        FROM event_participants ep
        JOIN passport_records pr ON ep.email = pr.user_email AND ep.event_id = pr.event_id
        WHERE ep.event_id = :event_id
        AND ep.status = 'confirmed'
        AND pr.record_id IS NOT NULL
    """)
    
    participants = db.execute(participants_query, {
        "event_id": event_id
    }).fetchall()
    
    if not participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No participants with passport data found"
        )
    
    # Format event dates
    event_dates = f"{event.start_date.strftime('%B %d, %Y')} - {event.end_date.strftime('%B %d, %Y')}"
    
    successful = 0
    failed = 0
    errors = []
    
    # Generate LOI for each participant
    for participant in participants:
        try:
            logger.info(f"Generating LOI for participant {participant.id}: {participant.full_name}")
            
            # Get passport data from external API
            passport_data = {}
            try:
                import os
                import requests
                
                API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{participant.record_id}"
                API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
                
                headers = {
                    'x-api-key': API_KEY,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
                
                payload = {"passport_id": participant.record_id}
                response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('result', {}).get('status') == 'success':
                        passport_data = response_data['result']['data']
            except Exception as e:
                logger.warning(f"Could not fetch passport data for participant {participant.id}: {e}")
            
            # Generate LOI PDF and upload to Cloudinary
            pdf_url, loi_slug = await generate_loi_document(
                participant_id=participant.id,
                event_id=event_id,
                template_html=template.template_content,
                participant_name=participant.full_name,
                passport_number=passport_data.get('passport_no'),
                nationality=passport_data.get('nationality'),
                date_of_birth=passport_data.get('date_of_birth'),
                passport_issue_date=passport_data.get('date_of_issue'),
                passport_expiry_date=passport_data.get('date_of_expiry'),
                event_name=event.event_name,
                event_dates=event_dates,
                event_location=event.event_location,
                organization_name='MSF'
            )
            
            # Store LOI record in database (optional - for tracking)
            try:
                db.execute(text("""
                    INSERT INTO participant_loi 
                    (participant_id, event_id, loi_url, loi_slug, generated_at)
                    VALUES (:participant_id, :event_id, :loi_url, :loi_slug, :generated_at)
                    ON CONFLICT (participant_id, event_id) 
                    DO UPDATE SET 
                        loi_url = :loi_url, 
                        loi_slug = :loi_slug, 
                        generated_at = :generated_at
                """), {
                    "participant_id": participant.id,
                    "event_id": event_id,
                    "loi_url": pdf_url,
                    "loi_slug": loi_slug,
                    "generated_at": datetime.utcnow()
                })
            except Exception as e:
                # Table might not exist, continue without storing
                logger.warning(f"Could not store LOI record: {e}")
            
            successful += 1
            logger.info(f"✅ LOI generated for {participant.full_name}: {pdf_url}")
            
        except Exception as e:
            failed += 1
            error_msg = f"Failed for {participant.full_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    db.commit()
    
    return {
        "message": "LOI generation completed",
        "total_participants": len(participants),
        "successful": successful,
        "failed": failed,
        "errors": errors if errors else None,
        "event_name": event.event_name,
        "template_name": template.template_name,
        "event_dates": event_dates
    }