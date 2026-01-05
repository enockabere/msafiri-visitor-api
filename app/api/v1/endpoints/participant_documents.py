"""
Participant Document Generation Endpoints

Generate certificates and badges for mobile app participants.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Any, List
import logging

from app.db.database import get_db
from app.api import deps
from app.services.certificate_generation import generate_certificate
from app.services.badge_generation import generate_badge

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/participants/{participant_id}/generate-documents")
async def generate_participant_documents(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Generate certificate and badge documents for a participant.
    Uses the certificate_name from travel details as the name on documents.
    """
    
    # Get participant details including certificate_name from travel details
    participant_query = text("""
        SELECT 
            ep.id,
            ep.full_name,
            ep.email,
            ep.event_id,
            ep.certificate_name,
            e.title as event_name,
            e.start_date,
            e.end_date,
            e.location as event_location
        FROM event_participants ep
        JOIN events e ON ep.event_id = e.id
        WHERE ep.id = :participant_id
        AND ep.user_id = :user_id
    """)
    
    participant = db.execute(participant_query, {
        "participant_id": participant_id,
        "user_id": current_user.id
    }).fetchone()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found or access denied"
        )
    
    if not participant.certificate_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate name not provided in travel details. Please update your travel information."
        )
    
    # Format event dates
    event_dates = f"{participant.start_date.strftime('%B %d, %Y')} - {participant.end_date.strftime('%B %d, %Y')}"
    
    generated_documents = []
    
    # Generate Certificate
    certificate_query = text("""
        SELECT 
            ec.id as event_certificate_id,
            ct.template_content,
            ct.name as template_name
        FROM event_certificates ec
        JOIN certificate_templates ct ON ec.certificate_template_id = ct.id
        WHERE ec.event_id = :event_id
        AND ec.tenant_id = (SELECT tenant_id FROM events WHERE id = :event_id)
    """)
    
    certificate_config = db.execute(certificate_query, {
        "event_id": participant.event_id
    }).fetchone()
    
    if certificate_config:
        try:
            # Check if certificate already exists
            existing_cert_query = text("""
                SELECT certificate_url FROM participant_certificates 
                WHERE event_certificate_id = :event_certificate_id 
                AND participant_id = :participant_id
            """)
            
            existing_cert = db.execute(existing_cert_query, {
                "event_certificate_id": certificate_config.event_certificate_id,
                "participant_id": participant_id
            }).fetchone()
            
            if existing_cert and existing_cert.certificate_url:
                certificate_url = existing_cert.certificate_url
            else:
                # Generate new certificate
                certificate_url = await generate_certificate(
                    participant_id=participant.id,
                    event_id=participant.event_id,
                    template_html=certificate_config.template_content,
                    participant_name=participant.full_name,
                    certificate_name=participant.certificate_name,
                    event_name=participant.event_name,
                    event_dates=event_dates,
                    event_location=participant.event_location
                )
                
                # Save certificate record
                if not existing_cert:
                    db.execute(text("""
                        INSERT INTO participant_certificates 
                        (event_certificate_id, participant_id, certificate_url, issued_at)
                        VALUES (:event_certificate_id, :participant_id, :certificate_url, :issued_at)
                    """), {
                        "event_certificate_id": certificate_config.event_certificate_id,
                        "participant_id": participant_id,
                        "certificate_url": certificate_url,
                        "issued_at": datetime.utcnow()
                    })
                else:
                    db.execute(text("""
                        UPDATE participant_certificates 
                        SET certificate_url = :certificate_url, issued_at = :issued_at
                        WHERE event_certificate_id = :event_certificate_id 
                        AND participant_id = :participant_id
                    """), {
                        "certificate_url": certificate_url,
                        "issued_at": datetime.utcnow(),
                        "event_certificate_id": certificate_config.event_certificate_id,
                        "participant_id": participant_id
                    })
            
            generated_documents.append({
                "type": "certificate",
                "name": f"{participant.event_name} - Certificate",
                "url": certificate_url,
                "template_name": certificate_config.template_name
            })
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {str(e)}")
    
    # Generate Badge
    badge_query = text("""
        SELECT 
            eb.id as event_badge_id,
            bt.template_content,
            bt.name as template_name,
            eb.template_variables
        FROM event_badges eb
        JOIN badge_templates bt ON eb.badge_template_id = bt.id
        WHERE eb.event_id = :event_id
        AND eb.tenant_id = (SELECT tenant_id FROM events WHERE id = :event_id)
    """)
    
    badge_config = db.execute(badge_query, {
        "event_id": participant.event_id
    }).fetchone()
    
    if badge_config:
        try:
            # Check if badge already exists
            existing_badge_query = text("""
                SELECT badge_url FROM participant_badges 
                WHERE event_badge_id = :event_badge_id 
                AND participant_id = :participant_id
            """)
            
            existing_badge = db.execute(existing_badge_query, {
                "event_badge_id": badge_config.event_badge_id,
                "participant_id": participant_id
            }).fetchone()
            
            if existing_badge and existing_badge.badge_url:
                badge_url = existing_badge.badge_url
            else:
                # Get tagline from template variables
                template_vars = badge_config.template_variables or {}
                tagline = template_vars.get('tagline', '')
                
                # Generate new badge
                badge_url = await generate_badge(
                    participant_id=participant.id,
                    event_id=participant.event_id,
                    template_html=badge_config.template_content,
                    participant_name=participant.full_name,
                    badge_name=participant.certificate_name,  # Use certificate_name as badge name
                    event_name=participant.event_name,
                    event_dates=event_dates,
                    event_location=participant.event_location,
                    tagline=tagline
                )
                
                # Save badge record
                if not existing_badge:
                    db.execute(text("""
                        INSERT INTO participant_badges 
                        (event_badge_id, participant_id, badge_url, issued_at)
                        VALUES (:event_badge_id, :participant_id, :badge_url, :issued_at)
                    """), {
                        "event_badge_id": badge_config.event_badge_id,
                        "participant_id": participant_id,
                        "badge_url": badge_url,
                        "issued_at": datetime.utcnow()
                    })
                else:
                    db.execute(text("""
                        UPDATE participant_badges 
                        SET badge_url = :badge_url, issued_at = :issued_at
                        WHERE event_badge_id = :event_badge_id 
                        AND participant_id = :participant_id
                    """), {
                        "badge_url": badge_url,
                        "issued_at": datetime.utcnow(),
                        "event_badge_id": badge_config.event_badge_id,
                        "participant_id": participant_id
                    })
            
            generated_documents.append({
                "type": "badge",
                "name": f"{participant.event_name} - Badge",
                "url": badge_url,
                "template_name": badge_config.template_name
            })
            
        except Exception as e:
            logger.error(f"Badge generation failed: {str(e)}")
    
    db.commit()
    
    if not generated_documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificate or badge templates configured for this event"
        )
    
    return {
        "message": "Documents generated successfully",
        "participant_name": participant.full_name,
        "certificate_name": participant.certificate_name,
        "event_name": participant.event_name,
        "documents": generated_documents
    }


@router.get("/participants/{participant_id}/documents")
async def get_participant_documents(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Get all generated documents for a participant.
    """
    
    # Verify participant belongs to current user
    participant_query = text("""
        SELECT ep.id, ep.full_name, ep.event_id, e.title as event_name
        FROM event_participants ep
        JOIN events e ON ep.event_id = e.id
        WHERE ep.id = :participant_id
        AND ep.user_id = :user_id
    """)
    
    participant = db.execute(participant_query, {
        "participant_id": participant_id,
        "user_id": current_user.id
    }).fetchone()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found or access denied"
        )
    
    documents = []
    
    # Get certificates
    cert_query = text("""
        SELECT 
            pc.certificate_url,
            pc.issued_at,
            ct.name as template_name
        FROM participant_certificates pc
        JOIN event_certificates ec ON pc.event_certificate_id = ec.id
        JOIN certificate_templates ct ON ec.certificate_template_id = ct.id
        WHERE pc.participant_id = :participant_id
        AND pc.certificate_url IS NOT NULL
    """)
    
    certificates = db.execute(cert_query, {"participant_id": participant_id}).fetchall()
    
    for cert in certificates:
        documents.append({
            "type": "certificate",
            "name": f"{participant.event_name} - Certificate",
            "url": cert.certificate_url,
            "issued_at": cert.issued_at.isoformat(),
            "template_name": cert.template_name
        })
    
    # Get badges
    badge_query = text("""
        SELECT 
            pb.badge_url,
            pb.issued_at,
            bt.name as template_name
        FROM participant_badges pb
        JOIN event_badges eb ON pb.event_badge_id = eb.id
        JOIN badge_templates bt ON eb.badge_template_id = bt.id
        WHERE pb.participant_id = :participant_id
        AND pb.badge_url IS NOT NULL
    """)
    
    badges = db.execute(badge_query, {"participant_id": participant_id}).fetchall()
    
    for badge in badges:
        documents.append({
            "type": "badge",
            "name": f"{participant.event_name} - Badge",
            "url": badge.badge_url,
            "issued_at": badge.issued_at.isoformat(),
            "template_name": badge.template_name
        })
    
    return {
        "participant_name": participant.full_name,
        "event_name": participant.event_name,
        "documents": documents
    }