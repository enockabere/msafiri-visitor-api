"""
Participant Proof of Accommodation API Endpoints

This module provides endpoints for mobile app to fetch proof of accommodation documents.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.guesthouse import AccommodationAllocation, VendorAccommodation

router = APIRouter()


@router.get("/events/{event_id}/participants/me/proof-of-accommodation")
async def get_my_proof_of_accommodation(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get proof of accommodation document for the current user's event participation.

    **Authentication:** Required (Bearer token)

    **Returns:**
    - has_proof: Boolean indicating if proof document exists
    - proof_url: Public URL to the PDF document
    - generated_at: Timestamp when proof was generated
    - hotel_name: Name of the accommodation
    - check_in_date: Check-in date
    - check_out_date: Check-out date
    - room_number: Room number (if assigned)
    - room_type: Room type (Single/Double)
    - confirmation_number: Booking confirmation number (extracted from PDF filename)
    """

    # Find the event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Find participant record for this user in this event
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()

    if not participant:
        raise HTTPException(
            status_code=404,
            detail="You are not registered for this event"
        )

    # Check if proof document exists
    if not hasattr(participant, 'proof_of_accommodation_url') or not participant.proof_of_accommodation_url:
        # Check if accommodation is allocated
        accommodation = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.guest_email == current_user.email,
            AccommodationAllocation.event_id == event_id,
            AccommodationAllocation.status != 'cancelled'
        ).first()

        return {
            "has_proof": False,
            "proof_url": None,
            "generated_at": None,
            "hotel_name": None,
            "check_in_date": None,
            "check_out_date": None,
            "room_number": None,
            "room_type": None,
            "confirmation_number": None,
            "message": "Accommodation allocated but proof document pending" if accommodation else "No accommodation assigned yet"
        }

    # Fetch accommodation details
    accommodation = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.guest_email == current_user.email,
        AccommodationAllocation.event_id == event_id,
        AccommodationAllocation.status != 'cancelled'
    ).first()

    hotel_name = None
    room_type = None
    room_number = None
    check_in_date = None
    check_out_date = None

    if accommodation:
        check_in_date = accommodation.check_in_date.isoformat() if accommodation.check_in_date else None
        check_out_date = accommodation.check_out_date.isoformat() if accommodation.check_out_date else None

        if accommodation.accommodation_type == 'vendor':
            vendor = db.query(VendorAccommodation).filter(
                VendorAccommodation.id == accommodation.vendor_accommodation_id
            ).first()
            if vendor:
                hotel_name = vendor.vendor_name
            room_type = accommodation.room_type.capitalize() if accommodation.room_type else None
        elif accommodation.accommodation_type == 'guesthouse':
            if accommodation.room and accommodation.room.guesthouse:
                hotel_name = accommodation.room.guesthouse.name
                room_number = accommodation.room.room_number
                room_type = "Shared" if accommodation.room.capacity > 1 else "Single"

    # Extract confirmation number from URL (last part of filename before .pdf)
    confirmation_number = None
    proof_url = getattr(participant, 'proof_of_accommodation_url', None)
    if proof_url:
        try:
            # URL format: https://.../proof-accommodation-{event_id}-{participant_id}-{timestamp}.pdf
            filename = proof_url.split('/')[-1]
            # Extract parts after "proof-accommodation-"
            parts = filename.replace('.pdf', '').split('-')
            if len(parts) >= 4:
                # Confirmation format: MSF-EVENT{eventId}-PART{participantId}-{random}
                confirmation_number = f"MSF-EVENT{parts[2]}-PART{parts[3]}"
                if len(parts) > 4:
                    confirmation_number += f"-{parts[4]}"
        except Exception:
            pass

    return {
        "has_proof": True,
        "proof_url": getattr(participant, 'proof_of_accommodation_url', None),
        "generated_at": getattr(participant, 'proof_generated_at', None).isoformat() if getattr(participant, 'proof_generated_at', None) else None,
        "hotel_name": hotel_name,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "room_number": room_number,
        "room_type": room_type,
        "confirmation_number": confirmation_number,
        "event_name": event.title,
        "participant_name": participant.full_name
    }
