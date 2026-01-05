"""
Participant Document Retrieval Endpoints

Retrieve generated certificates and badges for mobile app participants.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import logging

from app.db.database import get_db
from app.api import deps

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/participants/{participant_id}/documents")
async def get_participant_documents(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Get all generated documents (certificates and badges) for a participant.
    Only returns documents that have been generated from portal.
    """
    
    # Verify participant belongs to current user
    participant_query = text("""
        SELECT ep.id, ep.full_name, ep.event_id, e.title as event_name, ep.certificate_name
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
        "certificate_name": participant.certificate_name,
        "event_name": participant.event_name,
        "documents": documents,
        "message": "Documents will be available after event organizers generate them from the portal" if not documents else None
    }