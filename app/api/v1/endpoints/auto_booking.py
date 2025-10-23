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

@router.post("/events/{event_id}/auto-book-all-participants")
def auto_book_all_participants(
    event_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Automatically book accommodation for all confirmed participants with optimal pairing"""
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Get event and vendor accommodation
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
    
    # Get all confirmed participants with gender info
    participants_query = text("""
        SELECT ep.id, ep.full_name, ep.email, ep.role, pr.gender_identity
        FROM event_participants ep
        LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE ep.event_id = :event_id AND ep.status = 'confirmed'
        ORDER BY ep.role, pr.gender_identity, ep.id
    """)
    participants = db.execute(participants_query, {"event_id": event_id}).fetchall()
    
    if not participants:
        return {"message": "No confirmed participants found for this event"}
    
    # Group participants by role and gender
    facilitators = []
    male_visitors = []
    female_visitors = []
    other_visitors = []
    
    print(f"DEBUG: Processing {len(participants)} participants for grouping")
    for p in participants:
        print(f"DEBUG: Participant {p.full_name} - role: {p.role}, gender_identity: {p.gender_identity}")
        if p.role.lower() in ['facilitator', 'organizer']:
            facilitators.append(p)
            print(f"DEBUG: Added {p.full_name} to facilitators")
        else:
            gender = _normalize_gender(p.gender_identity)
            print(f"DEBUG: Normalized gender for {p.full_name}: {gender}")
            if gender == 'male':
                male_visitors.append(p)
                print(f"DEBUG: Added {p.full_name} to male_visitors")
            elif gender == 'female':
                female_visitors.append(p)
                print(f"DEBUG: Added {p.full_name} to female_visitors")
            else:
                other_visitors.append(p)
                print(f"DEBUG: Added {p.full_name} to other_visitors")
    
    results = []
    
    # Book facilitators in single rooms
    for facilitator in facilitators:
        try:
            result = _book_single_room(db, event, facilitator, tenant_id, current_user.id)
            results.append({"participant_id": facilitator.id, "participant_name": facilitator.full_name, "status": "success", "result": result})
        except Exception as e:
            results.append({"participant_id": facilitator.id, "participant_name": facilitator.full_name, "status": "error", "error": str(e)})
    
    # Book visitors - use individual booking logic that handles pairing automatically
    all_visitors = male_visitors + female_visitors
    print(f"DEBUG: Final grouping results:")
    print(f"DEBUG: Facilitators: {[f.full_name for f in facilitators]}")
    print(f"DEBUG: Male visitors: {[v.full_name for v in male_visitors]}")
    print(f"DEBUG: Female visitors: {[v.full_name for v in female_visitors]}")
    print(f"DEBUG: Other visitors: {[v.full_name for v in other_visitors]}")
    print(f"DEBUG: Total visitors to book: {len(all_visitors)}")
    
    for visitor in all_visitors:
        try:
            gender = _normalize_gender(visitor.gender_identity)
            print(f"DEBUG: Booking {visitor.full_name} (gender: {gender})")
            result = _book_visitor_room(db, event, visitor, gender, tenant_id, current_user.id)
            print(f"DEBUG: Result for {visitor.full_name}: {result}")
            results.append({"participant_id": visitor.id, "participant_name": visitor.full_name, "status": "success", "result": result})
        except Exception as e:
            print(f"DEBUG: Error booking {visitor.full_name}: {str(e)}")
            results.append({"participant_id": visitor.id, "participant_name": visitor.full_name, "status": "error", "error": str(e)})
    
    # Book other gender visitors in single rooms
    for visitor in other_visitors:
        try:
            result = _book_single_room(db, event, visitor, tenant_id, current_user.id)
            results.append({"participant_id": visitor.id, "participant_name": visitor.full_name, "status": "success", "result": result})
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
    """Automatically book accommodation for confirmed participant"""
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Get event and check for vendor event accommodation setup
    event_query = text("""
        SELECT e.id, e.title, e.start_date, e.end_date,
               vea.id as vendor_event_id, vea.vendor_accommodation_id,
               vea.single_rooms, vea.double_rooms
        FROM events e 
        LEFT JOIN vendor_event_accommodations vea ON e.id = vea.event_id
        WHERE e.id = :event_id AND e.tenant_id = :tenant_id
    """)
    event = db.execute(event_query, {"event_id": event_id, "tenant_id": tenant_id}).fetchone()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if not event.vendor_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No vendor accommodation setup found for this event"
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
    print(f"DEBUG: _normalize_gender input: '{gender_identity}'")
    if not gender_identity:
        print(f"DEBUG: _normalize_gender output: 'other' (no gender_identity)")
        return 'other'
    gender = gender_identity.lower()
    if gender in ['man', 'male']:
        print(f"DEBUG: _normalize_gender output: 'male'")
        return 'male'
    elif gender in ['woman', 'female']:
        print(f"DEBUG: _normalize_gender output: 'female'")
        return 'female'
    else:
        print(f"DEBUG: _normalize_gender output: 'other' (unrecognized: '{gender}')")
        return 'other'

def _book_single_room(db, event, participant, tenant_id, user_id):
    """Book a single room for participant"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    # Check single room availability in vendor event accommodation
    vendor_query = text("""
        SELECT single_rooms FROM vendor_event_accommodations 
        WHERE id = :vendor_event_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"vendor_event_id": event.vendor_event_id}).fetchone()
    
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
    
    # Update room count in vendor event accommodation
    db.execute(text("""
        UPDATE vendor_event_accommodations 
        SET single_rooms = single_rooms - 1 
        WHERE id = :vendor_event_id
    """), {"vendor_event_id": event.vendor_event_id})
    
    db.commit()
    return {"message": "Single room booked successfully", "allocation_id": allocation.id}

def _book_visitor_room(db, event, participant, gender, tenant_id, user_id):
    """Book room for visitor - try to match with same gender"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    print(f"DEBUG: Looking for match for {participant.full_name} (gender: {gender})")
    
    # Look for unmatched visitor of same gender in single rooms (exclude facilitators/organizers)
    unmatched_query = text("""
        SELECT aa.id, aa.participant_id, ep.full_name
        FROM accommodation_allocations aa
        JOIN event_participants ep ON aa.participant_id = ep.id
        JOIN public_registrations pr ON ep.id = pr.participant_id
        WHERE aa.event_id = :event_id
        AND aa.room_type = 'single' 
        AND aa.status = 'booked'
        AND ep.role = 'visitor'
        AND LOWER(pr.gender_identity) IN :gender_values
        ORDER BY aa.created_at DESC
        LIMIT 1
    """)
    
    gender_values = (['man', 'male'] if gender == 'male' else ['woman', 'female'])
    print(f"DEBUG: Searching for gender values: {gender_values}")
    
    unmatched = db.execute(unmatched_query, {
        "event_id": event.id,
        "gender_values": tuple(gender_values)
    }).fetchone()
    
    if unmatched:
        print(f"DEBUG: Found visitor match: {unmatched.full_name} (allocation_id: {unmatched.id})")
        # Merge with existing single room allocation to create double room
        return _merge_to_double_room(db, event, participant, unmatched, tenant_id, user_id)
    else:
        print(f"DEBUG: No visitor match found for {participant.full_name}, booking single room")
        # No match found, book single room temporarily
        return _book_single_room_temp(db, event, participant, tenant_id, user_id)

def _merge_to_double_room(db, event, new_participant, existing_allocation, tenant_id, user_id):
    """Merge two single room bookings into one double room"""
    from app import crud
    from app.schemas.accommodation import AccommodationAllocationCreate
    
    print(f"DEBUG: Merging {new_participant.full_name} with {existing_allocation.full_name}")
    
    # Update existing allocation to double room
    db.execute(text("""
        UPDATE accommodation_allocations 
        SET room_type = 'double', number_of_guests = 2
        WHERE id = :allocation_id
    """), {"allocation_id": existing_allocation.id})
    
    print(f"DEBUG: Updated existing allocation {existing_allocation.id} to double room")
    
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
    
    print(f"DEBUG: Created new allocation {new_allocation.id} for {new_participant.full_name}")
    
    # Update room counts (return 1 single, take 1 double)
    db.execute(text("""
        UPDATE vendor_event_accommodations 
        SET single_rooms = single_rooms + 1, double_rooms = double_rooms - 1
        WHERE id = :vendor_event_id
    """), {"vendor_event_id": event.vendor_event_id})
    
    print(f"DEBUG: Updated room counts: +1 single, -1 double")
    
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
        WHERE id = :vendor_event_id AND single_rooms > 0
    """)
    vendor = db.execute(vendor_query, {"vendor_event_id": event.vendor_event_id}).fetchone()
    
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
        UPDATE vendor_event_accommodations 
        SET single_rooms = single_rooms - 1 
        WHERE id = :vendor_event_id
    """), {"vendor_event_id": event.vendor_event_id})
    
    db.commit()
    return {
        "message": "Single room booked (waiting for potential match)",
        "allocation_id": allocation.id
    }