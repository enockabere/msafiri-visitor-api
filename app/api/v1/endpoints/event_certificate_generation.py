"""
Event Certificate Generation Endpoints

Generate certificates when configured in portal event management.
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
from app.services.certificate_generation import generate_certificate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/events/{event_id}/certificates/{certificate_id}/generate-all")
async def generate_certificates_for_event(
    event_id: int,
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Generate certificates for all participants who have provided certificate_name.
    Called when certificate is configured in portal event management.
    """
    
    # Check admin permission
    admin_roles = [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate certificates"
        )
    
    # Get event certificate configuration
    cert_config_query = text("""
        SELECT 
            ec.id,
            ec.template_variables,
            ct.template_content,
            ct.name as template_name,
            e.title as event_name,
            e.start_date,
            e.end_date,
            e.location as event_location
        FROM event_certificates ec
        JOIN certificate_templates ct ON ec.certificate_template_id = ct.id
        JOIN events e ON ec.event_id = e.id
        WHERE ec.id = :certificate_id
        AND ec.event_id = :event_id
    """)
    
    cert_config = db.execute(cert_config_query, {
        "certificate_id": certificate_id,
        "event_id": event_id
    }).fetchone()
    
    if not cert_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate configuration not found"
        )
    
    # Get participants who have provided certificate_name
    participants_query = text("""
        SELECT 
            ep.id,
            ep.full_name,
            ep.certificate_name,
            ep.email
        FROM event_participants ep
        WHERE ep.event_id = :event_id
        AND ep.certificate_name IS NOT NULL
        AND ep.certificate_name != ''
        AND ep.status = 'confirmed'
    """)
    
    participants = db.execute(participants_query, {
        "event_id": event_id
    }).fetchall()
    
    if not participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No participants have provided certificate names yet"
        )
    
    # Format event dates
    event_dates = f"{cert_config.start_date.strftime('%B %d, %Y')} - {cert_config.end_date.strftime('%B %d, %Y')}"
    
    successful = 0
    failed = 0
    errors = []
    
    # Generate certificate for each participant
    for participant in participants:
        try:
            logger.info(f"Generating certificate for participant {participant.id}: {participant.full_name}")
            
            # Check if certificate already exists
            existing_cert_query = text("""
                SELECT id FROM participant_certificates 
                WHERE event_certificate_id = :certificate_id 
                AND participant_id = :participant_id
            """)
            
            existing_cert = db.execute(existing_cert_query, {
                "certificate_id": certificate_id,
                "participant_id": participant.id
            }).fetchone()
            
            # Generate certificate PDF
            certificate_url = await generate_certificate(
                participant_id=participant.id,
                event_id=event_id,
                template_html=cert_config.template_content,
                participant_name=participant.full_name,
                certificate_name=participant.certificate_name,
                event_name=cert_config.event_name,
                event_dates=event_dates,
                event_location=cert_config.event_location
            )
            
            # Save or update certificate record
            if existing_cert:
                db.execute(text("""
                    UPDATE participant_certificates 
                    SET certificate_url = :certificate_url, issued_at = :issued_at
                    WHERE id = :cert_id
                """), {
                    "certificate_url": certificate_url,
                    "issued_at": datetime.utcnow(),
                    "cert_id": existing_cert.id
                })
            else:
                db.execute(text("""
                    INSERT INTO participant_certificates 
                    (event_certificate_id, participant_id, certificate_url, issued_at)
                    VALUES (:certificate_id, :participant_id, :certificate_url, :issued_at)
                """), {
                    "certificate_id": certificate_id,
                    "participant_id": participant.id,
                    "certificate_url": certificate_url,
                    "issued_at": datetime.utcnow()
                })
            
            successful += 1
            logger.info(f"✅ Certificate generated for {participant.full_name}: {certificate_url}")
            
        except Exception as e:
            failed += 1
            error_msg = f"Failed for {participant.full_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    db.commit()
    
    return {
        "message": "Certificate generation completed",
        "total_participants": len(participants),
        "successful": successful,
        "failed": failed,
        "errors": errors if errors else None,
        "event_name": cert_config.event_name,
        "template_name": cert_config.template_name
    }