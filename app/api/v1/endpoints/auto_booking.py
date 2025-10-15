from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.tenant import Tenant

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
    participant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Automatically book accommodation for confirmed participant"""
    return _auto_book_participant_internal(event_id, participant_id, db, current_user, tenant_context)

def _auto_book_participant_internal(
    event_id: int,
    participant_id: int,
    db: Session,
    current_user,
    tenant_context: str,
) -> Any:
    """Automatically book accommodation for confirmed participant"""
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Get event and linked vendor accommodation
    event_query = text("""
        SELECT e.id, e.title, e.vendor_accommodation_id, e.start_date, e.end_date
        FROM events e 
        WHERE e.id = :event_id AND e.tenant_id = :tenant_id
    """)
    event = db.execute(event_query, {"event_id": event_id, "tenant_id": tenant_id}).fetchone()
    
    if not event or not event.vendor_accommodation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event not found or no vendor accommodation linked"
        )
    
    # Get participant details
    participant_query = text("""
        SELECT ep.id, ep.full_name, ep.email, ep.role, pr.gender_identity
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
    
    # Check if already booked
    existing_booking = text("""
        SELECT id FROM accommodation_allocations 
        WHERE participant_id = :participant_id AND accommodation_type = 'vendor' 
        AND status IN ('booked', 'checked_in')
    """)
    if db.execute(existing_booking, {"participant_id": participant_id}).fetchone():
        return {"message": "Participant already has accommodation"}
    
    # Determine room type based on role
    role = participant.role.lower()
    if role in ['facilitator', 'organizer']:
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

def _book_single_room(db, event, participant, tenant_id, user_id):
    """Book a single room for participant"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    # Check single room availability
    vendor_query = text("""
        SELECT single_rooms FROM vendor_accommodations 
        WHERE id = :vendor_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"vendor_id": event.vendor_accommodation_id}).fetchone()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No single rooms available"
        )
    
    # Create allocation
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
        event_id=event.id
    )
    
    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )
    
    # Update room count
    db.execute(text("""
        UPDATE vendor_accommodations 
        SET single_rooms = single_rooms - 1 
        WHERE id = :vendor_id
    """), {"vendor_id": event.vendor_accommodation_id})
    
    db.commit()
    return {"message": "Single room booked successfully", "allocation_id": allocation.id}

def _book_visitor_room(db, event, participant, gender, tenant_id, user_id):
    """Book room for visitor - try to match with same gender"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    # Look for unmatched visitor of same gender
    unmatched_query = text("""
        SELECT aa.id, aa.participant_id, ep.full_name
        FROM accommodation_allocations aa
        JOIN event_participants ep ON aa.participant_id = ep.id
        JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE aa.vendor_accommodation_id = :vendor_id 
        AND aa.room_type = 'single' 
        AND aa.status = 'booked'
        AND ep.role NOT IN ('facilitator', 'organizer')
        AND LOWER(pr.gender_identity) IN :gender_values
        AND aa.created_at > NOW() - INTERVAL '1 hour'
        ORDER BY aa.created_at DESC
        LIMIT 1
    """)
    
    gender_values = (['man', 'male'] if gender == 'male' else ['woman', 'female'])
    unmatched = db.execute(unmatched_query, {
        "vendor_id": event.vendor_accommodation_id,
        "gender_values": tuple(gender_values)
    }).fetchone()
    
    if unmatched:
        # Merge with existing single room allocation
        return _merge_to_double_room(db, event, participant, unmatched, tenant_id, user_id)
    else:
        # Check if double rooms available
        vendor_query = text("""
            SELECT double_rooms FROM vendor_accommodations 
            WHERE id = :vendor_id AND double_rooms > 0
        """)
        vendor = db.execute(vendor_query, {"vendor_id": event.vendor_accommodation_id}).fetchone()
        
        if vendor:
            # Book double room (will wait for match)
            return _book_single_room_temp(db, event, participant, tenant_id, user_id)
        else:
            # No double rooms, book single
            return _book_single_room(db, event, participant, tenant_id, user_id)

def _merge_to_double_room(db, event, new_participant, existing_allocation, tenant_id, user_id):
    """Merge two single room bookings into one double room"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    # Update existing allocation to double room
    db.execute(text("""
        UPDATE accommodation_allocations 
        SET room_type = 'double', number_of_guests = 2
        WHERE id = :allocation_id
    """), {"allocation_id": existing_allocation.id})
    
    # Create new allocation for second person
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
        event_id=event.id
    )
    
    new_allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )
    
    # Update room counts (return 1 single, take 1 double)
    db.execute(text("""
        UPDATE vendor_accommodations 
        SET single_rooms = single_rooms + 1, double_rooms = double_rooms - 1
        WHERE id = :vendor_id
    """), {"vendor_id": event.vendor_accommodation_id})
    
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
        SELECT single_rooms FROM vendor_accommodations 
        WHERE id = :vendor_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"vendor_id": event.vendor_accommodation_id}).fetchone()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rooms available"
        )
    
    # Create allocation (single room, but can be merged later)
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
        event_id=event.id
    )
    
    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_data, tenant_id=tenant_id, user_id=user_id
    )
    
    # Update room count
    db.execute(text("""
        UPDATE vendor_accommodations 
        SET single_rooms = single_rooms - 1 
        WHERE id = :vendor_id
    """), {"vendor_id": event.vendor_accommodation_id})
    
    db.commit()
    return {
        "message": "Single room booked (waiting for potential match)",
        "allocation_id": allocation.id
    }