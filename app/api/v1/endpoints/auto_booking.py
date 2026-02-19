from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

def get_tenant_id_from_context(db, tenant_context, current_user):
    """Helper function to get tenant ID from context"""
    if tenant_context.isdigit():
        return int(tenant_context)
    else:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
        return tenant.id if tenant else current_user.tenant_id

router = APIRouter()

@router.post("/events/{event_id}/auto-book-participant")
def auto_book_participant(
    event_id: int,
    request_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Automatically book accommodation for confirmed participant"""
    participant_id = request_data.get("participant_id")
    if not participant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="participant_id is required"
        )
    return _auto_book_participant_internal(event_id, participant_id, db, current_user, tenant_context)

@router.post("/events/{event_id}/refresh-accommodations")
def refresh_event_accommodations(
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """
    Refresh all accommodations for an event by clearing existing bookings and re-booking
    with optimal pairing. This ensures visitors of the same gender are paired into double rooms.
    """
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)

    # Get event and verify it hasn't started yet
    event_query = text("""
        SELECT e.id, e.title, e.start_date, e.end_date
        FROM events e
        WHERE e.id = :event_id AND e.tenant_id = :tenant_id
    """)
    event = db.execute(event_query, {"event_id": event_id, "tenant_id": tenant_id}).fetchone()

    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    from datetime import datetime
    if event.start_date and event.start_date <= datetime.now().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refresh accommodations - event has already started"
        )

    # Clear all existing vendor accommodation allocations for this event
    existing_allocations = db.execute(text("""
        SELECT id, room_type FROM accommodation_allocations
        WHERE event_id = :event_id AND accommodation_type = 'vendor' AND status IN ('booked', 'checked_in')
    """), {"event_id": event_id}).fetchall()

    # Restore room counts
    single_count = len([a for a in existing_allocations if a.room_type == 'single'])
    double_count = len([a for a in existing_allocations if a.room_type == 'double'])

    # Double rooms are shared by 2 people, so divide by 2 to get actual room count
    double_room_count = double_count // 2

    if existing_allocations:
        db.execute(text("""
            UPDATE vendor_event_accommodations
            SET single_rooms = single_rooms + :single_count,
                double_rooms = double_rooms + :double_count
            WHERE event_id = :event_id
        """), {"event_id": event_id, "single_count": single_count, "double_count": double_room_count})

        # Delete all existing allocations
        db.execute(text("""
            DELETE FROM accommodation_allocations
            WHERE event_id = :event_id AND accommodation_type = 'vendor' AND status IN ('booked', 'checked_in')
        """), {"event_id": event_id})

        db.commit()
        logger.info(f"Cleared {len(existing_allocations)} allocations for event {event_id}")

    # Now re-book all participants with optimal pairing
    result = auto_book_all_participants(event_id, db, current_user, tenant_context)

    return {
        "message": "Accommodations refreshed successfully",
        "cleared_allocations": len(existing_allocations),
        "booking_result": result
    }


@router.post("/events/{event_id}/auto-book-all-participants")
def auto_book_all_participants(
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Automatically book accommodation for all confirmed participants who are staying at venue with optimal pairing"""

    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)

    # Get event with accommodation setup
    event_query = text("""
        SELECT e.id, e.title, e.vendor_accommodation_id, e.start_date, e.end_date,
               vea.id as accommodation_setup_id, vea.single_rooms, vea.double_rooms
        FROM events e
        LEFT JOIN vendor_event_accommodations vea ON e.id = vea.event_id
        WHERE e.id = :event_id AND e.tenant_id = :tenant_id
    """)
    event = db.execute(event_query, {"event_id": event_id, "tenant_id": tenant_id}).fetchone()

    if not event or not event.accommodation_setup_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event not found or no accommodation setup linked"
        )

    # Get all confirmed participants who are STAYING AT VENUE (not travelling daily) with gender info
    # Use COALESCE to check gender_identity in both event_participants and public_registrations
    participants_query = text("""
        SELECT ep.id, ep.full_name, ep.email, ep.role, ep.participant_role,
               COALESCE(ep.gender_identity, pr.gender_identity) as gender_identity,
               ep.accommodation_preference
        FROM event_participants ep
        LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE ep.event_id = :event_id
        AND ep.status = 'confirmed'
        AND ep.accommodation_preference = 'staying_at_venue'
        ORDER BY ep.participant_role, ep.role, COALESCE(ep.gender_identity, pr.gender_identity), ep.id
    """)
    participants = db.execute(participants_query, {"event_id": event_id}).fetchall()

    # Also count those travelling daily for reporting
    travelling_daily_count = db.execute(text("""
        SELECT COUNT(*) as count FROM event_participants
        WHERE event_id = :event_id AND status = 'confirmed' AND accommodation_preference = 'travelling_daily'
    """), {"event_id": event_id}).fetchone().count

    if not participants:
        return {
            "message": "No confirmed participants staying at venue found for this event",
            "travelling_daily_count": travelling_daily_count
        }
    
    # Group participants by role and gender
    facilitators = []
    male_visitors = []
    female_visitors = []
    other_visitors = []

    for p in participants:
        # Check BOTH role fields - if EITHER says facilitator/organizer, they get single room
        role_value = (p.role or '').lower()
        participant_role_value = (p.participant_role or '').lower()
        is_facilitator = role_value in ['facilitator', 'organizer'] or participant_role_value in ['facilitator', 'organizer']
        if is_facilitator:
            facilitators.append(p)
        else:
            gender = _normalize_gender(p.gender_identity)
            if gender == 'male':
                male_visitors.append(p)
            elif gender == 'female':
                female_visitors.append(p)
            else:
                other_visitors.append(p)
    
    results = []

    # Book facilitators in single rooms
    for facilitator in facilitators:
        try:
            result = _book_single_room(db, event, facilitator, tenant_id, current_user.id)
            results.append({"participant_id": facilitator.id, "participant_name": facilitator.full_name, "status": "success", "result": result, "room_type": "single"})
        except Exception as e:
            results.append({"participant_id": facilitator.id, "participant_name": facilitator.full_name, "status": "error", "error": str(e)})

    # Book visitors with optimal pairing - pair same gender visitors into double rooms
    # Male visitors
    male_pairs = []
    for i in range(0, len(male_visitors) - 1, 2):
        male_pairs.append((male_visitors[i], male_visitors[i + 1]))
    male_unpaired = male_visitors[-1:] if len(male_visitors) % 2 == 1 else []

    # Female visitors
    female_pairs = []
    for i in range(0, len(female_visitors) - 1, 2):
        female_pairs.append((female_visitors[i], female_visitors[i + 1]))
    female_unpaired = female_visitors[-1:] if len(female_visitors) % 2 == 1 else []

    # Book paired visitors in double rooms
    for visitor1, visitor2 in male_pairs + female_pairs:
        try:
            result = _book_paired_double_room(db, event, visitor1, visitor2, tenant_id, current_user.id)
            results.append({"participant_id": visitor1.id, "participant_name": visitor1.full_name, "status": "success", "result": result, "room_type": "double", "paired_with": visitor2.full_name})
            results.append({"participant_id": visitor2.id, "participant_name": visitor2.full_name, "status": "success", "result": result, "room_type": "double", "paired_with": visitor1.full_name})
        except Exception as e:
            results.append({"participant_id": visitor1.id, "participant_name": visitor1.full_name, "status": "error", "error": str(e)})
            results.append({"participant_id": visitor2.id, "participant_name": visitor2.full_name, "status": "error", "error": str(e)})

    # Book unpaired visitors in single rooms
    for visitor in male_unpaired + female_unpaired + other_visitors:
        try:
            result = _book_single_room(db, event, visitor, tenant_id, current_user.id)
            results.append({"participant_id": visitor.id, "participant_name": visitor.full_name, "status": "success", "result": result, "room_type": "single"})
        except Exception as e:
            results.append({"participant_id": visitor.id, "participant_name": visitor.full_name, "status": "error", "error": str(e)})
    
    success_count = len([r for r in results if r["status"] == "success"])
    error_count = len([r for r in results if r["status"] == "error"])
    
    return {
        "message": f"Processed {len(participants)} participants: {success_count} successful, {error_count} errors",
        "total_participants": len(participants),
        "successful_bookings": success_count,
        "failed_bookings": error_count,
        "results": results
    }

def _auto_book_participant_internal(
    event_id: int,
    participant_id: int,
    db: Session,
    current_user,
    tenant_context: str,
) -> Any:
    """Automatically book accommodation for confirmed participant who is staying at venue"""

    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)

    # Get event with accommodation setup
    event_query = text("""
        SELECT e.id, e.title, e.start_date, e.end_date, e.vendor_accommodation_id,
               vea.id as accommodation_setup_id, vea.single_rooms, vea.double_rooms
        FROM events e
        LEFT JOIN vendor_event_accommodations vea ON e.id = vea.event_id
        WHERE e.id = :event_id AND e.tenant_id = :tenant_id
    """)
    event = db.execute(event_query, {"event_id": event_id, "tenant_id": tenant_id}).fetchone()

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Auto-booking query - event_id: {event_id}, tenant_id: {tenant_id}")
    logger.info(f"Event query result: {dict(event._mapping) if event and hasattr(event, '_mapping') else 'None'}")

    if not event:
        logger.info(f"No event found for event_id {event_id} and tenant_id {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if not event.accommodation_setup_id:
        logger.info(f"No accommodation_setup_id found for event {event_id}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No vendor accommodation setup found for this event"
        )

    # Get participant details including accommodation_preference
    # Use COALESCE to check gender_identity in both event_participants and public_registrations
    participant_query = text("""
        SELECT ep.id, ep.full_name, ep.email, ep.role, ep.participant_role,
               COALESCE(ep.gender_identity, pr.gender_identity) as gender_identity,
               ep.accommodation_preference
        FROM event_participants ep
        LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE ep.id = :participant_id AND ep.event_id = :event_id AND ep.status = 'confirmed'
    """)
    participant = db.execute(participant_query, {
        "participant_id": participant_id,
        "event_id": event_id
    }).fetchone()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Confirmed participant not found"
        )

    # Check if participant is staying at venue - skip booking for those travelling daily
    if participant.accommodation_preference != 'staying_at_venue':
        logger.info(f"Participant {participant_id} is travelling daily - skipping auto-booking")
        return {
            "message": "Skipped - participant is travelling daily to the event",
            "participant_name": participant.full_name,
            "accommodation_preference": participant.accommodation_preference
        }
    
    # Check if already booked
    existing_booking = text("""
        SELECT id FROM accommodation_allocations 
        WHERE participant_id = :participant_id AND accommodation_type = 'vendor' 
        AND status IN ('booked', 'checked_in')
    """)
    if db.execute(existing_booking, {"participant_id": participant_id}).fetchone():
        return {"message": "Participant already has accommodation"}
    
    # Determine room type based on role - check BOTH role fields
    role_value = (participant.role or '').lower()
    participant_role_value = (participant.participant_role or '').lower()
    is_facilitator = role_value in ['facilitator', 'organizer'] or participant_role_value in ['facilitator', 'organizer']
    if is_facilitator:
        room_type = 'single'
        return _book_single_room(db, event, participant, tenant_id, current_user.id)
    else:
        # Visitor - try to match with same gender for double room
        gender = _normalize_gender(participant.gender_identity)
        if gender == 'other':
            room_type = 'single'
            return _book_single_room(db, event, participant, tenant_id, current_user.id)
        else:
            return _book_visitor_room(db, event, participant, gender, tenant_id, current_user.id)

def _normalize_gender(gender_identity):
    """Convert registration gender to standard format"""
    if not gender_identity:
        return 'other'
    gender = gender_identity.lower()
    if gender in ['man', 'male']:
        return 'male'
    elif gender in ['woman', 'female']:
        return 'female'
    else:
        return 'other'

def _get_vendor_rate_for_board_type(db, vendor_accommodation_id, board_type):
    """Get the rate for a specific board type from vendor accommodation"""
    vendor_query = text("""
        SELECT rate_bed_breakfast, rate_half_board, rate_full_board, rate_bed_only, rate_currency
        FROM vendor_accommodations WHERE id = :vendor_id
    """)
    vendor = db.execute(vendor_query, {"vendor_id": vendor_accommodation_id}).fetchone()

    if not vendor:
        return None, 'KES'

    rate = None
    if board_type == 'FullBoard':
        rate = vendor.rate_full_board
    elif board_type == 'HalfBoard':
        rate = vendor.rate_half_board
    elif board_type == 'BedAndBreakfast':
        rate = vendor.rate_bed_breakfast
    elif board_type == 'BedOnly':
        rate = vendor.rate_bed_only

    return rate, vendor.rate_currency or 'KES'

def _get_event_board_type(db, event_id):
    """Get accommodation_type from event"""
    event_query = text("SELECT accommodation_type FROM events WHERE id = :event_id")
    result = db.execute(event_query, {"event_id": event_id}).fetchone()
    return result.accommodation_type if result else None

def _book_single_room(db, event, participant, tenant_id, user_id):
    """Book a single room for participant"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate

    # Check single room availability in vendor event accommodation
    vendor_query = text("""
        SELECT single_rooms FROM vendor_event_accommodations
        WHERE id = :accommodation_setup_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"accommodation_setup_id": event.accommodation_setup_id}).fetchone()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No single rooms available"
        )

    # Get board type from event and rate from vendor
    board_type = _get_event_board_type(db, event.id)
    rate_per_day, rate_currency = _get_vendor_rate_for_board_type(db, event.vendor_accommodation_id, board_type)

    # Create allocation with board_type and rate
    allocation_data = AccommodationAllocationCreate(
        guest_name=participant.full_name,
        guest_email=participant.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=1,
        accommodation_type="vendor",
        vendor_accommodation_id=event.vendor_accommodation_id,
        room_type="single",
        participant_id=participant.id,
        event_id=event.id,
        board_type=board_type,
        rate_per_day=rate_per_day,
        rate_currency=rate_currency
    )

    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )

    # Update room count in vendor event accommodation
    db.execute(text("""
        UPDATE vendor_event_accommodations
        SET single_rooms = single_rooms - 1
        WHERE id = :accommodation_setup_id
    """), {"accommodation_setup_id": event.accommodation_setup_id})

    db.commit()

    return {"message": "Single room booked successfully", "allocation_id": allocation.id}


def _book_paired_double_room(db, event, visitor1, visitor2, tenant_id, user_id):
    """Book two visitors together in a double room"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate

    # Check double room availability
    vendor_query = text("""
        SELECT double_rooms FROM vendor_event_accommodations
        WHERE id = :accommodation_setup_id AND double_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"accommodation_setup_id": event.accommodation_setup_id}).fetchone()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No double rooms available"
        )

    # Get board type from event and rate from vendor
    board_type = _get_event_board_type(db, event.id)
    rate_per_day, rate_currency = _get_vendor_rate_for_board_type(db, event.vendor_accommodation_id, board_type)

    # Create allocation for first visitor
    allocation_data1 = AccommodationAllocationCreate(
        guest_name=visitor1.full_name,
        guest_email=visitor1.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=2,
        accommodation_type="vendor",
        vendor_accommodation_id=event.vendor_accommodation_id,
        room_type="double",
        participant_id=visitor1.id,
        event_id=event.id,
        board_type=board_type,
        rate_per_day=rate_per_day,
        rate_currency=rate_currency
    )

    allocation1 = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data1, tenant_id=tenant_id, user_id=user_id
    )

    # Create allocation for second visitor (same double room)
    allocation_data2 = AccommodationAllocationCreate(
        guest_name=visitor2.full_name,
        guest_email=visitor2.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=2,
        accommodation_type="vendor",
        vendor_accommodation_id=event.vendor_accommodation_id,
        room_type="double",
        participant_id=visitor2.id,
        event_id=event.id,
        board_type=board_type,
        rate_per_day=rate_per_day,
        rate_currency=rate_currency
    )

    allocation2 = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data2, tenant_id=tenant_id, user_id=user_id
    )

    # Update room count (take 1 double room)
    db.execute(text("""
        UPDATE vendor_event_accommodations
        SET double_rooms = double_rooms - 1
        WHERE id = :accommodation_setup_id
    """), {"accommodation_setup_id": event.accommodation_setup_id})

    db.commit()

    return {
        "message": f"Double room booked for {visitor1.full_name} and {visitor2.full_name}",
        "allocation_ids": [allocation1.id, allocation2.id]
    }


def _book_visitor_room(db, event, participant, gender, tenant_id, user_id):
    """Book room for visitor - try to match with same gender"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Looking for match for {participant.full_name} (gender: {gender})")

    # Look for unmatched visitor of same gender in single rooms (exclude facilitators/organizers)
    # Use COALESCE to check gender in both event_participants and public_registrations
    # Also use LEFT JOIN so participants without public_registrations are still found
    # Check BOTH role and participant_role fields to exclude facilitators/organizers
    unmatched_query = text("""
        SELECT aa.id, aa.participant_id, ep.full_name
        FROM accommodation_allocations aa
        JOIN event_participants ep ON aa.participant_id = ep.id
        LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE aa.event_id = :event_id
        AND aa.room_type = 'single'
        AND aa.status = 'booked'
        AND LOWER(COALESCE(ep.role, '')) NOT IN ('facilitator', 'organizer')
        AND LOWER(COALESCE(ep.participant_role, '')) NOT IN ('facilitator', 'organizer')
        AND LOWER(COALESCE(ep.gender_identity, pr.gender_identity, '')) IN :gender_values
        AND aa.participant_id != :current_participant_id
        ORDER BY aa.created_at ASC
        LIMIT 1
    """)

    gender_values = (['man', 'male'] if gender == 'male' else ['woman', 'female'])
    logger.info(f"Searching for gender values: {gender_values}")
    
    unmatched = db.execute(unmatched_query, {
        "event_id": event.id,
        "gender_values": tuple(gender_values),
        "current_participant_id": participant.id
    }).fetchone()
    
    if unmatched:
        logger.info(f"Found visitor match: {unmatched.full_name} (allocation_id: {unmatched.id})")
        # Merge with existing single room allocation to create double room
        return _merge_to_double_room(db, event, participant, unmatched, tenant_id, user_id)
    else:
        logger.info(f"No visitor match found for {participant.full_name}, booking single room")
        # No match found, book single room temporarily
        return _book_single_room_temp(db, event, participant, tenant_id, user_id)

def _merge_to_double_room(db, event, new_participant, existing_allocation, tenant_id, user_id):
    """Merge two single room bookings into one double room"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate

    # Get board type from event and rate from vendor
    board_type = _get_event_board_type(db, event.id)
    rate_per_day, rate_currency = _get_vendor_rate_for_board_type(db, event.vendor_accommodation_id, board_type)

    # Update existing allocation to double room with board_type and rate
    db.execute(text("""
        UPDATE accommodation_allocations
        SET room_type = 'double', number_of_guests = 2,
            board_type = :board_type, rate_per_day = :rate_per_day, rate_currency = :rate_currency
        WHERE id = :allocation_id
    """), {
        "allocation_id": existing_allocation.id,
        "board_type": board_type,
        "rate_per_day": rate_per_day,
        "rate_currency": rate_currency
    })

    # Create new allocation for second person with board_type and rate
    allocation_data = AccommodationAllocationCreate(
        guest_name=new_participant.full_name,
        guest_email=new_participant.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=1,
        accommodation_type="vendor",
        vendor_accommodation_id=event.vendor_accommodation_id,
        room_type="double",
        participant_id=new_participant.id,
        event_id=event.id,
        board_type=board_type,
        rate_per_day=rate_per_day,
        rate_currency=rate_currency
    )

    new_allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )

    # Update room counts (return 1 single, take 1 double)
    db.execute(text("""
        UPDATE vendor_event_accommodations
        SET single_rooms = single_rooms + 1, double_rooms = double_rooms - 1
        WHERE id = :accommodation_setup_id
    """), {"accommodation_setup_id": event.accommodation_setup_id})

    db.commit()

    return {
        "message": f"Matched with {existing_allocation.full_name} in double room",
        "allocation_id": new_allocation.id,
        "matched_with": existing_allocation.full_name
    }



def _book_single_room_temp(db, event, participant, tenant_id, user_id):
    """Book single room temporarily (waiting for match)"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate

    # Check single room availability
    vendor_query = text("""
        SELECT single_rooms FROM vendor_event_accommodations
        WHERE id = :accommodation_setup_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"accommodation_setup_id": event.accommodation_setup_id}).fetchone()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rooms available"
        )

    # Get board type from event and rate from vendor
    board_type = _get_event_board_type(db, event.id)
    rate_per_day, rate_currency = _get_vendor_rate_for_board_type(db, event.vendor_accommodation_id, board_type)

    # Create allocation (single room, but can be merged later) with board_type and rate
    allocation_data = AccommodationAllocationCreate(
        guest_name=participant.full_name,
        guest_email=participant.email,
        check_in_date=event.start_date,
        check_out_date=event.end_date,
        number_of_guests=1,
        accommodation_type="vendor",
        vendor_accommodation_id=event.vendor_accommodation_id,
        room_type="single",
        participant_id=participant.id,
        event_id=event.id,
        board_type=board_type,
        rate_per_day=rate_per_day,
        rate_currency=rate_currency
    )

    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )

    # Update room count
    db.execute(text("""
        UPDATE vendor_event_accommodations
        SET single_rooms = single_rooms - 1
        WHERE id = :accommodation_setup_id
    """), {"accommodation_setup_id": event.accommodation_setup_id})

    db.commit()

    # After booking, try to re-pair visitors to optimize room usage
    _try_repair_visitors(db, event, tenant_id, user_id)

    return {
        "message": "Single room booked (waiting for potential match)",
        "allocation_id": allocation.id
    }


def _try_repair_visitors(db, event, tenant_id, user_id):
    """
    Re-pair unpaired visitors of the same gender into double rooms.
    This runs after each booking to optimize room assignments.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Running re-pairing for event {event.id}")

    # Get all unpaired visitors (single rooms) grouped by gender
    # Check BOTH role and participant_role fields to exclude facilitators/organizers
    unpaired_query = text("""
        SELECT aa.id as allocation_id, aa.participant_id, ep.full_name, ep.role, ep.participant_role,
               LOWER(COALESCE(ep.gender_identity, pr.gender_identity, '')) as gender
        FROM accommodation_allocations aa
        JOIN event_participants ep ON aa.participant_id = ep.id
        LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE aa.event_id = :event_id
        AND aa.room_type = 'single'
        AND aa.status = 'booked'
        AND LOWER(COALESCE(ep.role, '')) NOT IN ('facilitator', 'organizer')
        AND LOWER(COALESCE(ep.participant_role, '')) NOT IN ('facilitator', 'organizer')
        ORDER BY gender, aa.created_at ASC
    """)

    unpaired = db.execute(unpaired_query, {"event_id": event.id}).fetchall()
    logger.info(f"Found {len(unpaired)} unpaired visitors")

    # Group by gender
    male_unpaired = [p for p in unpaired if p.gender in ('man', 'male')]
    female_unpaired = [p for p in unpaired if p.gender in ('woman', 'female')]

    # Pair males
    while len(male_unpaired) >= 2:
        visitor1 = male_unpaired.pop(0)
        visitor2 = male_unpaired.pop(0)
        logger.info(f"Pairing males: {visitor1.full_name} with {visitor2.full_name}")
        _pair_visitors(db, event, visitor1, visitor2)

    # Pair females
    while len(female_unpaired) >= 2:
        visitor1 = female_unpaired.pop(0)
        visitor2 = female_unpaired.pop(0)
        logger.info(f"Pairing females: {visitor1.full_name} with {visitor2.full_name}")
        _pair_visitors(db, event, visitor1, visitor2)

    db.commit()
    logger.info("Re-pairing completed")


def _pair_visitors(db, event, visitor1, visitor2):
    """Pair two visitors into a double room"""
    # Get board type and rate
    board_type = _get_event_board_type(db, event.id)
    rate_per_day, rate_currency = _get_vendor_rate_for_board_type(db, event.vendor_accommodation_id, board_type)

    # Update both allocations to double room
    db.execute(text("""
        UPDATE accommodation_allocations
        SET room_type = 'double', number_of_guests = 2,
            board_type = :board_type, rate_per_day = :rate_per_day, rate_currency = :rate_currency
        WHERE id IN (:id1, :id2)
    """), {
        "id1": visitor1.allocation_id,
        "id2": visitor2.allocation_id,
        "board_type": board_type,
        "rate_per_day": rate_per_day,
        "rate_currency": rate_currency
    })

    # Update room counts (return 2 singles, take 1 double)
    db.execute(text("""
        UPDATE vendor_event_accommodations
        SET single_rooms = single_rooms + 2, double_rooms = double_rooms - 1
        WHERE id = :accommodation_setup_id
    """), {"accommodation_setup_id": event.accommodation_setup_id})
