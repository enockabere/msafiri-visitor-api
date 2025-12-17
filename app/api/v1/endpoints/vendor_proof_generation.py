"""
Vendor Hotel Proof of Accommodation Generation Endpoints

Manual proof generation for vendor accommodations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Any
import logging
import asyncio

from app.db.database import get_db
from app.api import deps
from app.models.user import UserRole
from app.services.proof_of_accommodation import generate_proof_of_accommodation

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/vendor-hotels/{vendor_id}/events/{event_id}/generate-proofs")
async def generate_proofs_for_vendor_hotel(
    vendor_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
) -> Any:
    """
    Generate proof of accommodation documents for all participants
    with accommodation allocated from this vendor hotel for a specific event.

    **Requires:** Admin role
    **Returns:** Count of proofs generated successfully
    """

    # Check admin permission
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can generate proof documents"
        )

    # Get vendor hotel details with template
    vendor_query = text("""
        SELECT va.vendor_name, va.location, va.accommodation_template
        FROM vendor_accommodations va
        WHERE va.id = :vendor_id
    """)
    vendor = db.execute(vendor_query, {"vendor_id": vendor_id}).fetchone()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor hotel not found"
        )

    if not vendor.accommodation_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This vendor hotel has no proof template configured. Please add a template first."
        )

    # Get event details
    event_query = text("""
        SELECT id, title, start_date, end_date
        FROM events
        WHERE id = :event_id
    """)
    event = db.execute(event_query, {"event_id": event_id}).fetchone()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get all participants with accommodation from this vendor hotel
    participants_query = text("""
        SELECT DISTINCT
            ep.id,
            ep.full_name,
            ep.email,
            aa.room_type,
            aa.id as allocation_id
        FROM event_participants ep
        JOIN accommodation_allocations aa ON ep.id = aa.participant_id
        WHERE aa.event_id = :event_id
        AND aa.vendor_accommodation_id = :vendor_id
        AND aa.status != 'cancelled'
    """)

    participants = db.execute(participants_query, {
        "event_id": event_id,
        "vendor_id": vendor_id
    }).fetchall()

    if not participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No participants found with accommodation from this vendor hotel"
        )

    # Format dates
    check_in_date = event.start_date.strftime('%B %d, %Y') if event.start_date else 'TBD'
    check_out_date = event.end_date.strftime('%B %d, %Y') if event.end_date else 'TBD'
    event_dates = f"{check_in_date} - {check_out_date}"

    successful = 0
    failed = 0
    errors = []

    # Generate proof for each participant
    for participant in participants:
        try:
            logger.info(f"Generating proof for participant {participant.id}: {participant.full_name}")

            # Generate proof PDF
            pdf_url = await generate_proof_of_accommodation(
                participant_id=participant.id,
                event_id=event.id,
                template_html=vendor.accommodation_template,
                hotel_name=vendor.vendor_name,
                hotel_address=vendor.location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                room_type=participant.room_type.capitalize() if participant.room_type else "Standard",
                event_name=event.title,
                event_dates=event_dates,
                participant_name=participant.full_name,
                room_number=None
            )

            # Update participant record with proof URL
            db.execute(text("""
                UPDATE event_participants
                SET proof_of_accommodation_url = :proof_url,
                    proof_generated_at = :generated_at
                WHERE id = :participant_id
            """), {
                "proof_url": pdf_url,
                "generated_at": datetime.utcnow(),
                "participant_id": participant.id
            })

            successful += 1
            logger.info(f"✅ Proof generated for {participant.full_name}: {pdf_url}")

        except Exception as e:
            failed += 1
            error_msg = f"Failed for {participant.full_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")

    db.commit()

    return {
        "message": f"Proof generation completed",
        "total_participants": len(participants),
        "successful": successful,
        "failed": failed,
        "errors": errors if errors else None,
        "vendor_hotel": vendor.vendor_name,
        "event": event.title
    }
