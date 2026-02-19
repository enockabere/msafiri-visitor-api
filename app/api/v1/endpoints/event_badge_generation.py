"""
Event Badge Generation Endpoints

Generate badges when configured in portal event management.
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
from app.services.badge_generation import generate_badge

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/events/{event_id}/badges/{badge_id}/generate-all")
async def generate_badges_for_event(
    event_id: int,
    badge_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Generate badges for all participants who have provided certificate_name.
    Called when badge is configured in portal event management.
    """
    
    # Check admin permission
    admin_roles = [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    if current_user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can generate badges"
        )
    
    # Get event badge configuration
    badge_config_query = text("""
        SELECT
            eb.id,
            eb.template_variables,
            bt.template_content,
            bt.name as template_name,
            bt.logo_url,
            bt.avatar_url,
            bt.enable_qr_code,
            e.title as event_name,
            e.start_date,
            e.end_date,
            e.location as event_location
        FROM event_badges eb
        JOIN badge_templates bt ON eb.badge_template_id = bt.id
        JOIN events e ON eb.event_id = e.id
        WHERE eb.id = :badge_id
        AND eb.event_id = :event_id
    """)
    
    badge_config = db.execute(badge_config_query, {
        "badge_id": badge_id,
        "event_id": event_id
    }).fetchone()
    
    if not badge_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge configuration not found"
        )
    
    # Get participants who have provided badge_name or certificate_name
    participants_query = text("""
        SELECT
            ep.id,
            ep.full_name,
            ep.certificate_name,
            ep.badge_name,
            ep.email
        FROM event_participants ep
        WHERE ep.event_id = :event_id
        AND (ep.badge_name IS NOT NULL AND ep.badge_name != ''
             OR ep.certificate_name IS NOT NULL AND ep.certificate_name != '')
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
    event_dates = f"{badge_config.start_date.strftime('%B %d, %Y')} - {badge_config.end_date.strftime('%B %d, %Y')}"
    
    # Get tagline from template variables
    template_vars = badge_config.template_variables or {}
    tagline = template_vars.get('tagline', '')
    
    successful = 0
    failed = 0
    errors = []
    
    # Generate badge for each participant
    for participant in participants:
        try:
            logger.info(f"Generating badge for participant {participant.id}: {participant.full_name}")
            
            # Check if badge already exists
            existing_badge_query = text("""
                SELECT id FROM participant_badges 
                WHERE event_badge_id = :badge_id 
                AND participant_id = :participant_id
            """)
            
            existing_badge = db.execute(existing_badge_query, {
                "badge_id": badge_id,
                "participant_id": participant.id
            }).fetchone()
            
            # Use badge_name if available, otherwise certificate_name, otherwise full_name
            display_badge_name = participant.badge_name or participant.certificate_name or participant.full_name

            # Generate badge PDF
            badge_url = await generate_badge(
                participant_id=participant.id,
                event_id=event_id,
                template_html=badge_config.template_content,
                participant_name=participant.full_name,
                badge_name=display_badge_name,
                event_name=badge_config.event_name,
                event_dates=event_dates,
                tagline=tagline,
                logo_url=badge_config.logo_url or "",
                avatar_url=badge_config.avatar_url or ""
            )
            
            # Save or update badge record
            if existing_badge:
                db.execute(text("""
                    UPDATE participant_badges 
                    SET badge_url = :badge_url, issued_at = :issued_at
                    WHERE id = :badge_id
                """), {
                    "badge_url": badge_url,
                    "issued_at": datetime.utcnow(),
                    "badge_id": existing_badge.id
                })
            else:
                db.execute(text("""
                    INSERT INTO participant_badges 
                    (event_badge_id, participant_id, badge_url, issued_at)
                    VALUES (:badge_id, :participant_id, :badge_url, :issued_at)
                """), {
                    "badge_id": badge_id,
                    "participant_id": participant.id,
                    "badge_url": badge_url,
                    "issued_at": datetime.utcnow()
                })
            
            successful += 1
            logger.info(f"✅ Badge generated for {participant.full_name}: {badge_url}")
            
        except Exception as e:
            failed += 1
            error_msg = f"Failed for {participant.full_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    db.commit()
    
    return {
        "message": "Badge generation completed",
        "total_participants": len(participants),
        "successful": successful,
        "failed": failed,
        "errors": errors if errors else None,
        "event_name": badge_config.event_name,
        "template_name": badge_config.template_name,
        "tagline": tagline
    }
