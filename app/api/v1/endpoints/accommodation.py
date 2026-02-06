from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.tenant import Tenant
from sqlalchemy import text

def get_tenant_id_from_context(db, tenant_context, current_user):
    """Helper function to get tenant ID from context"""
    if tenant_context and tenant_context.isdigit():
        return int(tenant_context)
    else:
        # Look up tenant by slug
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
        if tenant:
            return tenant.id
        else:
            # Try to look up by current_user.tenant_id (which might be a slug)
            if isinstance(current_user.tenant_id, str):
                tenant = db.query(Tenant).filter(Tenant.slug == current_user.tenant_id).first()
                if tenant:
                    return tenant.id
            return 1  # Fallback to default tenant

router = APIRouter()

@router.get("/test")
def test_accommodation_endpoint():
    """Test endpoint to verify accommodation router is working"""
    return {"message": "Accommodation router is working", "timestamp": "2024-10-15"}

@router.get("/available-participants")
def get_available_participants(
    event_id: int,
    accommodation_type: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get participants available for booking based on accommodation type"""
    from app.models.event_participant import EventParticipant
    from app.models.guesthouse import AccommodationAllocation
    from sqlalchemy import text
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Get all confirmed participants for the event
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.status == "confirmed"
    ).all()
    
    # Get participants who already have bookings for this accommodation type
    booked_participant_ids = db.query(AccommodationAllocation.participant_id).filter(
        AccommodationAllocation.accommodation_type == accommodation_type,
        AccommodationAllocation.status.in_(["booked", "checked_in"]),
        AccommodationAllocation.tenant_id == tenant_id
    ).subquery()
    
    # Filter out already booked participants
    available_participants = []
    for participant in participants:
        # Check if participant is already booked for this accommodation type
        is_booked = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant.id,
            AccommodationAllocation.accommodation_type == accommodation_type,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).first()
        
        if not is_booked:
            # Get gender from registration
            gender_result = db.execute(text(
                "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
            ), {"participant_id": participant.id}).fetchone()
            
            gender = None
            if gender_result and gender_result[0]:
                reg_gender = gender_result[0].lower()
                if reg_gender in ['man', 'male']:
                    gender = 'male'
                elif reg_gender in ['woman', 'female']:
                    gender = 'female'
                else:
                    gender = 'other'
            
            available_participants.append({
                "id": participant.id,
                "name": participant.full_name,
                "email": participant.email,
                "role": participant.role,
                "gender": gender
            })
    
    return available_participants

# GuestHouse endpoints
@router.get("/guesthouses", response_model=List[schemas.GuestHouse])
def get_guesthouses(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all guesthouses for tenant"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    guesthouses = crud.guesthouse.get_by_tenant(db, tenant_id=tenant_id)
    return guesthouses

@router.post("/guesthouses", response_model=schemas.GuestHouse)
def create_guesthouse(
    *,
    db: Session = Depends(get_db),
    guesthouse_in: schemas.GuestHouseCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create new guesthouse"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    guesthouse = crud.guesthouse.create_with_tenant(
        db, obj_in=guesthouse_in, tenant_id=tenant_id, created_by=current_user.email
    )
    return guesthouse

# Room endpoints
@router.get("/guesthouses/{guesthouse_id}/rooms", response_model=List[schemas.Room])
def get_rooms(
    guesthouse_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get all rooms for a guesthouse"""
    rooms = crud.room.get_by_guesthouse(db, guesthouse_id=guesthouse_id)
    # Rooms already have current_occupants field from the model
    return rooms

@router.get("/rooms", response_model=List[schemas.Room])
def get_all_rooms(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all rooms for tenant"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    rooms = crud.room.get_by_tenant(db, tenant_id=tenant_id)
    return rooms

@router.get("/rooms/{room_id}/occupants")
def get_room_occupants(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get room occupant details including gender"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Get room
    room = crud.room.get(db, id=room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Get active allocations for this room
    from app.models.guesthouse import AccommodationAllocation
    from app.models.event_participant import EventParticipant
    from app.models.user import User
    
    allocations = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.room_id == room_id,
        AccommodationAllocation.status.in_(["booked", "checked_in"])
    ).all()
    
    occupants = []
    occupant_genders = []
    
    for allocation in allocations:
        if allocation.participant_id:
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == allocation.participant_id
            ).first()
            if participant:
                user = db.query(User).filter(User.email == participant.email).first()
                if user:
                    occupants.append({
                        "name": user.full_name,
                        "email": user.email,
                        "gender": user.gender
                    })
                    if user.gender:
                        occupant_genders.append(user.gender)
    
    return {
        "room_id": room_id,
        "room_number": room.room_number,
        "capacity": room.capacity,
        "current_occupants": room.current_occupants,
        "occupants": occupants,
        "occupant_genders": list(set(occupant_genders)),
        "can_accept_gender": {
            "male": len(occupant_genders) == 0 or all(g == "male" for g in occupant_genders),
            "female": len(occupant_genders) == 0 or all(g == "female" for g in occupant_genders),
            "other": len(occupant_genders) == 0 and room.current_occupants == 0
        }
    }

@router.post("/rooms", response_model=schemas.Room)
def create_room(
    *,
    db: Session = Depends(get_db),
    room_in: schemas.RoomCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create new room"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    room = crud.room.create_with_tenant(db, obj_in=room_in, tenant_id=tenant_id)
    return room

# Room Allocation endpoints
@router.post("/allocations", response_model=schemas.AccommodationAllocation)
def create_allocation(
    allocation_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create accommodation allocation for guest house or vendor"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Convert dict to schema object for CRUD operation
    from app.schemas.accommodation import AccommodationAllocationCreate
    allocation_schema = AccommodationAllocationCreate(**allocation_data)
    
    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_schema, tenant_id=tenant_id, user_id=current_user.id
    )
    return allocation

@router.post("/room-allocations", response_model=schemas.AccommodationAllocation)
def create_room_allocation(
    allocation_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Allocate visitor to room with gender validation"""
    print(f"[DEBUG] DEBUG: ===== ROOM ALLOCATION ENDPOINT REACHED =====")
    print(f"[DEBUG] DEBUG: Request method: POST")
    print(f"[DEBUG] DEBUG: Request path: /room-allocations")
    print(f"[DEBUG] DEBUG: User: {current_user.email}, Tenant: {tenant_context}")
    print(f"[DEBUG] DEBUG: Allocation data: {allocation_data}")
    print(f"[DEBUG] DEBUG: User role: {current_user.role}")
    
    try:
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
            print(f"[DEBUG] DEBUG: Permission denied for role: {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Check for existing bookings to prevent double booking
        if allocation_data.get("participant_id"):
            from app.models.guesthouse import AccommodationAllocation
            existing_booking = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.participant_id == allocation_data["participant_id"],
                AccommodationAllocation.accommodation_type == allocation_data.get("accommodation_type"),
                AccommodationAllocation.status.in_(["booked", "checked_in"])
            ).first()
            
            if existing_booking:
                accom_type = "guesthouse" if allocation_data.get("accommodation_type") == "guesthouse" else "vendor hotel"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Participant already has a {accom_type} booking. Cannot book the same accommodation type twice."
                )
        
        # Validate gender compatibility for room sharing
        if allocation_data.get("room_id") and allocation_data.get("participant_id"):
            room = crud.room.get(db, id=allocation_data["room_id"])
            if room and room.capacity > 1:
                # Get participant's gender from registration
                from sqlalchemy import text
                gender_result = db.execute(text(
                    "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                ), {"participant_id": allocation_data["participant_id"]}).fetchone()
                
                if gender_result and gender_result[0]:
                    reg_gender = gender_result[0].lower()
                    # If gender is not male or female, check if room is empty
                    if reg_gender not in ['man', 'male', 'woman', 'female']:
                        if room.current_occupants > 0:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Users with non-binary gender cannot share rooms. Please select an empty room or use vendor accommodation."
                            )
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        
        # Convert dict to schema object for CRUD operation
        from app.schemas.accommodation import AccommodationAllocationCreate
        allocation_schema = AccommodationAllocationCreate(**allocation_data)
        
        allocation = crud.accommodation_allocation.create_with_tenant(
            db, obj_in=allocation_schema, tenant_id=tenant_id, user_id=current_user.id
        )
        print(f"[DEBUG] DEBUG: ===== ALLOCATION CREATED SUCCESSFULLY: {allocation.id} =====")
        return allocation
        
    except Exception as e:
        print(f"[DEBUG] DEBUG: Error creating allocation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating allocation: {str(e)}"
        )

# Vendor Accommodation endpoints
@router.get("/vendor-accommodations", response_model=List[schemas.VendorAccommodation])
def get_vendor_accommodations(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all vendor accommodations for tenant"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    vendors = crud.vendor_accommodation.get_by_tenant(db, tenant_id=tenant_id)
    return vendors

@router.get("/vendor-accommodations/{vendor_id}", response_model=schemas.VendorAccommodation)
def get_vendor_accommodation(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get single vendor accommodation by ID"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    vendor = crud.vendor_accommodation.get(db, id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor accommodation not found"
        )
    
    if vendor.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vendor accommodation"
        )
    
    return vendor

@router.post("/vendor-accommodations", response_model=schemas.VendorAccommodation)
def create_vendor_accommodation(
    *,
    db: Session = Depends(get_db),
    vendor_in: schemas.VendorAccommodationCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create new vendor accommodation"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    vendor = crud.vendor_accommodation.create_with_tenant(
        db, obj_in=vendor_in, tenant_id=tenant_id
    )
    return vendor

@router.post("/vendor-allocations")
def create_vendor_allocation(
    allocation_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Allocate visitor to vendor accommodation with room type validation"""
    try:
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Check for existing vendor bookings
        if allocation_data.get("participant_id"):
            from app.models.guesthouse import AccommodationAllocation
            existing_booking = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.participant_id == allocation_data["participant_id"],
                AccommodationAllocation.accommodation_type == "vendor",
                AccommodationAllocation.status.in_(["booked", "checked_in"])
            ).first()
            
            if existing_booking:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Participant already has a vendor hotel booking."
                )
        
        # Validate vendor accommodation and room type
        vendor_id = allocation_data.get("vendor_accommodation_id")
        room_type = allocation_data.get("room_type")  # "single" or "double"
        event_id = allocation_data.get("event_id")
        
        if not vendor_id or not room_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor accommodation ID and room type are required"
            )
        
        if not event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID is required for vendor accommodation booking"
            )
        
        vendor = crud.vendor_accommodation.get(db, id=vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor accommodation not found"
            )
        
        # 🔥 CRITICAL FIX: Validate vendor is set up for this specific event
        from app.models.guesthouse import VendorEventAccommodation
        vendor_event_setup = db.query(VendorEventAccommodation).filter(
            VendorEventAccommodation.vendor_accommodation_id == vendor_id,
            VendorEventAccommodation.event_id == event_id,
            VendorEventAccommodation.tenant_id == tenant_id,
            VendorEventAccommodation.is_active == True
        ).first()
        
        if not vendor_event_setup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hotel '{vendor.vendor_name}' is not available for this event. Please contact admin to set up accommodation for this event."
            )
        
        print(f"[HOTEL] VALIDATION: Vendor {vendor.vendor_name} is properly set up for event {event_id}")
        
        # Check room availability based on type using event-specific setup
        if room_type == "single":
            if vendor_event_setup.single_rooms <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No single rooms available at {vendor.vendor_name} for this event"
                )
            print(f"[HOTEL] AVAILABILITY: {vendor_event_setup.single_rooms} single rooms available for event {event_id}")
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room type must be 'single' or 'double'"
            )
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        
        # Create allocation(s) - handle room allocation logic
        participant_ids = allocation_data.get("participant_ids", [allocation_data.get("participant_id")])
        allocations = []
        
        if room_type == "double":
            # For double rooms, allocate 2 people per room
            rooms_needed = (len(participant_ids) + 1) // 2  # Ceiling division
            if vendor_event_setup.double_rooms < rooms_needed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough double rooms available at {vendor.vendor_name} for this event. Need {rooms_needed}, have {vendor_event_setup.double_rooms}"
                )
            vendor_event_setup.double_rooms -= rooms_needed
            print(f"[HOTEL] BOOKING: Reserved {rooms_needed} double rooms for event {event_id}")
        else:
            # For single rooms, allocate 1 person per room
            if vendor_event_setup.single_rooms < len(participant_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough single rooms available at {vendor.vendor_name} for this event. Need {len(participant_ids)}, have {vendor_event_setup.single_rooms}"
                )
            vendor_event_setup.single_rooms -= len(participant_ids)
            print(f"[HOTEL] BOOKING: Reserved {len(participant_ids)} single rooms for event {event_id}")
        
        for participant_id in participant_ids:
            if participant_id:
                allocation_data_copy = allocation_data.copy()
                allocation_data_copy["participant_id"] = participant_id
                allocation_data_copy["accommodation_type"] = "vendor"
                allocation_data_copy["room_type"] = room_type
                
                from app.schemas.accommodation import AccommodationAllocationCreate
                allocation_schema = AccommodationAllocationCreate(**allocation_data_copy)
                
                allocation = crud.accommodation_allocation.create_with_tenant(
                    db, obj_in=allocation_schema, tenant_id=tenant_id, user_id=current_user.id
                )
                allocations.append(allocation)
        
        # Update event setup occupancy
        vendor_event_setup.current_occupants += len(participant_ids)
        
        # Commit vendor event setup changes
        db.commit()
        print(f"[HOTEL] SUCCESS: Updated event setup occupancy to {vendor_event_setup.current_occupants}")
        
        # Return serialized response
        if len(allocations) == 1:
            allocation = allocations[0]
            return {
                "id": allocation.id,
                "guest_name": allocation.guest_name,
                "accommodation_type": allocation.accommodation_type,
                "vendor_accommodation_id": allocation.vendor_accommodation_id,
                "room_type": allocation.room_type,
                "status": allocation.status,
                "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None
            }
        else:
            return [{
                "id": allocation.id,
                "guest_name": allocation.guest_name,
                "accommodation_type": allocation.accommodation_type,
                "vendor_accommodation_id": allocation.vendor_accommodation_id,
                "room_type": allocation.room_type,
                "status": allocation.status,
                "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None
            } for allocation in allocations]
        
    except Exception as e:
        db.rollback()
        print(f"[HOTEL] ERROR: Failed to create vendor allocation: {str(e)}")
        print(f"[HOTEL] ERROR: Event ID: {allocation_data.get('event_id')}, Vendor ID: {allocation_data.get('vendor_accommodation_id')}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating vendor allocation: {str(e)}"
        )

@router.put("/vendor-accommodations/{vendor_id}", response_model=schemas.VendorAccommodation)
def update_vendor_accommodation(
    vendor_id: int,
    vendor_in: schemas.VendorAccommodationUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Update vendor accommodation"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    vendor = crud.vendor_accommodation.get(db, id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor accommodation not found"
        )
    
    if vendor.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this vendor accommodation"
        )
    
    vendor = crud.vendor_accommodation.update(db, db_obj=vendor, obj_in=vendor_in)
    return vendor

@router.delete("/vendor-accommodations/{vendor_id}")
def delete_vendor_accommodation(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Delete vendor accommodation"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    vendor = crud.vendor_accommodation.get(db, id=vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor accommodation not found"
        )
    
    # Verify vendor belongs to the tenant
    if vendor.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this vendor accommodation"
        )
    
    crud.vendor_accommodation.remove(db, id=vendor_id)
    return {"message": "Vendor accommodation deleted successfully"}

@router.post("/vendor-event-setup", response_model=schemas.VendorEventAccommodation)
def create_vendor_event_setup(
    *,
    db: Session = Depends(get_db),
    setup_data: schemas.VendorEventAccommodationCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Setup event-specific accommodation capacity for vendor hotel"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Verify vendor accommodation exists and belongs to tenant
    vendor = crud.vendor_accommodation.get(db, id=setup_data.vendor_accommodation_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor accommodation not found"
        )
    
    if vendor.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to setup this vendor accommodation"
        )
    
    # Check if setup already exists for this vendor and event
    from app.models.guesthouse import VendorEventAccommodation
    
    # Check for existing setup based on event_id or event_name
    if setup_data.event_id:
        existing_setup = db.query(VendorEventAccommodation).filter(
            VendorEventAccommodation.vendor_accommodation_id == setup_data.vendor_accommodation_id,
            VendorEventAccommodation.event_id == setup_data.event_id,
            VendorEventAccommodation.tenant_id == tenant_id,
            VendorEventAccommodation.is_active == True
        ).first()
    else:
        existing_setup = db.query(VendorEventAccommodation).filter(
            VendorEventAccommodation.vendor_accommodation_id == setup_data.vendor_accommodation_id,
            VendorEventAccommodation.event_name == setup_data.event_name,
            VendorEventAccommodation.tenant_id == tenant_id,
            VendorEventAccommodation.is_active == True
        ).first()
    
    if existing_setup:
        event_identifier = setup_data.event_name if setup_data.event_name else f"Event ID {setup_data.event_id}"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event accommodation setup already exists for this vendor and {event_identifier}"
        )
    
    # Calculate total capacity
    total_capacity = setup_data.single_rooms + (setup_data.double_rooms * 2)
    
    # Create vendor event accommodation setup
    vendor_event_setup = VendorEventAccommodation(
        tenant_id=tenant_id,
        vendor_accommodation_id=setup_data.vendor_accommodation_id,
        event_id=setup_data.event_id,
        event_name=setup_data.event_name,
        single_rooms=setup_data.single_rooms,
        double_rooms=setup_data.double_rooms,
        total_capacity=total_capacity,
        current_occupants=0,
        is_active=setup_data.is_active,
        created_by=current_user.email
    )
    
    db.add(vendor_event_setup)
    db.commit()
    db.refresh(vendor_event_setup)
    
    return vendor_event_setup

@router.get("/vendor-event-setups/{vendor_id}")
def get_vendor_event_setups(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all event setups for a vendor accommodation with event details"""
    print(f"[HOTEL] DEBUG: ===== GET VENDOR EVENT SETUPS ENDPOINT CALLED =====")
    print(f"[HOTEL] DEBUG: Vendor ID: {vendor_id}, Tenant: {tenant_context}")
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    from app.models.guesthouse import VendorEventAccommodation, AccommodationAllocation
    from app.models.event import Event
    
    print(f"[HOTEL] DEBUG: Querying setups for vendor {vendor_id}, tenant {tenant_id}")
    setups = db.query(VendorEventAccommodation).filter(
        VendorEventAccommodation.vendor_accommodation_id == vendor_id,
        VendorEventAccommodation.tenant_id == tenant_id,
        VendorEventAccommodation.is_active == True
    ).all()
    print(f"[HOTEL] DEBUG: Found {len(setups)} setups for vendor {vendor_id}")
    
    # Build response with event details and calculate actual occupants
    result = []
    print(f"[HOTEL] DEBUG: Processing {len(setups)} setups...")
    for setup in setups:
        print(f"[HOTEL] DEBUG: Processing setup {setup.id} for event {setup.event_id}")
        # Calculate current occupants from actual allocations for this vendor and event
        current_occupants = 0
        if setup.event_id:
            print(f"[HOTEL] DEBUG: Counting allocations for setup {setup.id}, event {setup.event_id}, vendor {setup.vendor_accommodation_id}")
            # Count allocations for this specific vendor accommodation and event
            allocations_query = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.event_id == setup.event_id,
                AccommodationAllocation.vendor_accommodation_id == setup.vendor_accommodation_id,
                AccommodationAllocation.accommodation_type == "vendor",
                AccommodationAllocation.status.in_(["booked", "checked_in"]),
                AccommodationAllocation.tenant_id == tenant_id
            )
            allocations_list = allocations_query.all()
            current_occupants = len(allocations_list)
            print(f"[HOTEL] DEBUG: Found {current_occupants} allocations for setup {setup.id}")
            for alloc in allocations_list:
                print(f"[HOTEL] DEBUG: - Allocation {alloc.id}: {alloc.guest_name}, status={alloc.status}")
            
            # Update the setup's current_occupants in the database
            setup.current_occupants = current_occupants
            db.commit()
            print(f"[HOTEL] DEBUG: Updated setup {setup.id} current_occupants to {current_occupants}")
        else:
            print(f"[HOTEL] DEBUG: Setup {setup.id} has no event_id, skipping occupancy calculation")
            print(f"[HOTEL] DEBUG: Setup {setup.id} event_name: {setup.event_name}")
            # Try to find allocations by event name if no event_id
            if setup.event_name:
                # Find event by name
                event = db.query(Event).filter(Event.title == setup.event_name).first()
                if event:
                    print(f"[HOTEL] DEBUG: Found event {event.id} for setup {setup.id} by name '{setup.event_name}'")
                    # Count allocations using the found event_id
                    allocations_query = db.query(AccommodationAllocation).filter(
                        AccommodationAllocation.event_id == event.id,
                        AccommodationAllocation.vendor_accommodation_id == setup.vendor_accommodation_id,
                        AccommodationAllocation.accommodation_type == "vendor",
                        AccommodationAllocation.status.in_(["booked", "checked_in"]),
                        AccommodationAllocation.tenant_id == tenant_id
                    )
                    allocations_list = allocations_query.all()
                    current_occupants = len(allocations_list)
                    print(f"[HOTEL] DEBUG: Found {current_occupants} allocations for setup {setup.id} by event name")
                    for alloc in allocations_list:
                        print(f"[HOTEL] DEBUG: - Allocation {alloc.id}: {alloc.guest_name}, status={alloc.status}")
                    
                    # Update the setup with the correct event_id and occupants
                    setup.event_id = event.id
                    setup.current_occupants = current_occupants
                    db.commit()
                    print(f"[HOTEL] DEBUG: Updated setup {setup.id} with event_id {event.id} and {current_occupants} occupants")
                else:
                    print(f"[HOTEL] DEBUG: No event found with name '{setup.event_name}' for setup {setup.id}")
        
        # Calculate room usage instead of person occupancy
        single_rooms_used = 0
        double_rooms_used = 0
        
        if setup.event_id:
            # Count single room allocations
            single_rooms_used = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.event_id == setup.event_id,
                AccommodationAllocation.vendor_accommodation_id == setup.vendor_accommodation_id,
                AccommodationAllocation.accommodation_type == "vendor",
                AccommodationAllocation.room_type == "single",
                AccommodationAllocation.status.in_(["booked", "checked_in"]),
                AccommodationAllocation.tenant_id == tenant_id
            ).count()
            
            # Count double room allocations (2 people per room)
            double_allocations = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.event_id == setup.event_id,
                AccommodationAllocation.vendor_accommodation_id == setup.vendor_accommodation_id,
                AccommodationAllocation.accommodation_type == "vendor",
                AccommodationAllocation.room_type == "double",
                AccommodationAllocation.status.in_(["booked", "checked_in"]),
                AccommodationAllocation.tenant_id == tenant_id
            ).count()
            double_rooms_used = (double_allocations + 1) // 2  # Round up for partial room usage
            
            print(f"[HOTEL] DEBUG: Setup {setup.id} room usage: {single_rooms_used}S used, {double_rooms_used}D used")
        
        # Calculate remaining capacity
        remaining_single = setup.single_rooms - single_rooms_used
        remaining_double = setup.double_rooms - double_rooms_used
        remaining_capacity = remaining_single + (remaining_double * 2)
        
        setup_data = {
            "id": setup.id,
            "event_id": setup.event_id,
            "event_name": setup.event_name,
            "single_rooms": remaining_single,
            "double_rooms": remaining_double,
            "total_capacity": remaining_capacity,
            "current_occupants": current_occupants,
            "rooms_used": {
                "single_rooms_used": single_rooms_used,
                "double_rooms_used": double_rooms_used
            },
            "event": None
        }
        
        # Add event details if event_id exists
        if setup.event_id:
            event = db.query(Event).filter(Event.id == setup.event_id).first()
            if event:
                setup_data["event"] = {
                    "title": event.title,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "end_date": event.end_date.isoformat() if event.end_date else None
                }
        
        result.append(setup_data)
        print(f"[HOTEL] DEBUG: Added setup {setup.id} to result with {current_occupants} occupants")
    
    print(f"[HOTEL] DEBUG: Returning {len(result)} setups for vendor {vendor_id}")
    return result

# Dashboard endpoints
@router.get("/dashboard/overview")
def get_accommodation_overview(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get accommodation overview for dashboard"""
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    guesthouses = crud.guesthouse.get_by_tenant(db, tenant_id=tenant_id)
    overview = []
    
    for gh in guesthouses:
        rooms = crud.room.get_by_guesthouse(db, guesthouse_id=gh.id)
        total_capacity = sum(room.capacity for room in rooms)
        current_occupancy = sum(room.current_occupants for room in rooms)
        occupied_rooms = sum(1 for room in rooms if room.current_occupants > 0)
        
        overview.append({
            "id": gh.id,
            "name": gh.name,
            "total_rooms": len(rooms),
            "occupied_rooms": occupied_rooms,
            "available_rooms": len(rooms) - occupied_rooms,
            "total_capacity": total_capacity,
            "current_occupancy": current_occupancy
        })
    
    return {"guesthouses": overview}

@router.get("/allocations")
def get_allocations(
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all allocations for tenant with complete related data"""
    try:
        print(f"[HOTEL] DEBUG: ===== GET ALLOCATIONS ENDPOINT CALLED =====")
        print(f"[HOTEL] DEBUG: Starting get_allocations for tenant_context: {tenant_context}")
        print(f"[HOTEL] DEBUG: Event ID filter: {event_id}")
        print(f"[HOTEL] DEBUG: User: {current_user.email}")
        
        from app.models.guesthouse import AccommodationAllocation, Room, GuestHouse, VendorAccommodation
        from app.models.event import Event
        from app.models.event_participant import EventParticipant
        from app.models.user import User
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        print(f"[HOTEL] DEBUG: Resolved tenant_id: {tenant_id}")
        
        query = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.tenant_id == tenant_id
        )
        
        if event_id:
            query = query.filter(AccommodationAllocation.event_id == event_id)
            print(f"DEBUG: Filtering by event_id: {event_id}")
        
        allocations = query.all()
        print(f"[HOTEL] DEBUG: Found {len(allocations)} allocations")
        print(f"[HOTEL] DEBUG: ===== ALLOCATIONS ENDPOINT COMPLETE =====")
        
        result = []
        for allocation in allocations:
            print(f"DEBUG: Processing allocation {allocation.id}")
            
            allocation_data = {
                "id": allocation.id,
                "guest_name": allocation.guest_name,
                "guest_email": allocation.guest_email or "",
                "guest_phone": allocation.guest_phone or "",
                "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else "",
                "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else "",
                "number_of_guests": allocation.number_of_guests,
                "accommodation_type": allocation.accommodation_type,
                "status": allocation.status,
                "room_type": allocation.room_type,  # Include room type
                "room": None,
                "vendor_accommodation": None,
                "event": None,
                "participant": None
            }
            
            # Get room data
            if allocation.room_id:
                print(f"DEBUG: Fetching room data for room_id: {allocation.room_id}")
                room = db.query(Room).filter(Room.id == allocation.room_id).first()
                if room:
                    guesthouse = db.query(GuestHouse).filter(GuestHouse.id == room.guesthouse_id).first()
                    allocation_data["room"] = {
                        "id": room.id,
                        "room_number": room.room_number,
                        "capacity": room.capacity,
                        "current_occupants": room.current_occupants,
                        "guesthouse": {
                            "name": guesthouse.name if guesthouse else "Unknown Guesthouse"
                        }
                    }
                    print(f"DEBUG: Room data added: {allocation_data['room']}")
                else:
                    print(f"DEBUG: Room not found for room_id: {allocation.room_id}")
            
            # Get vendor data
            if allocation.vendor_accommodation_id:
                print(f"DEBUG: Fetching vendor data for vendor_id: {allocation.vendor_accommodation_id}")
                vendor = db.query(VendorAccommodation).filter(
                    VendorAccommodation.id == allocation.vendor_accommodation_id
                ).first()
                if vendor:
                    # Get roommate info for double rooms
                    roommate_name = None
                    if allocation.room_type == "double":
                        try:
                            # Get current participant's gender
                            current_gender = None
                            if allocation.participant_id:
                                gender_result = db.execute(text(
                                    "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                                ), {"participant_id": allocation.participant_id}).fetchone()
                                if gender_result and gender_result[0]:
                                    current_gender = gender_result[0]
                            
                            # Find roommate with same gender, excluding self
                            if current_gender:
                                roommate_query = text("""
                                    SELECT aa.guest_name 
                                    FROM accommodation_allocations aa
                                    JOIN public_registrations pr ON aa.participant_id = pr.participant_id
                                    WHERE aa.vendor_accommodation_id = :vendor_id 
                                    AND aa.room_type = 'double'
                                    AND aa.id != :current_allocation_id
                                    AND aa.status IN ('booked', 'checked_in')
                                    AND pr.gender_identity = :gender
                                    LIMIT 1
                                """)
                                roommate_result = db.execute(roommate_query, {
                                    "vendor_id": allocation.vendor_accommodation_id,
                                    "current_allocation_id": allocation.id,
                                    "gender": current_gender
                                }).fetchone()
                                if roommate_result:
                                    roommate_name = roommate_result.guest_name
                        except Exception as e:
                            roommate_name = None
                    
                    allocation_data["vendor_accommodation"] = {
                        "id": vendor.id,
                        "vendor_name": vendor.vendor_name,
                        "capacity": vendor.capacity,
                        "current_occupants": vendor.current_occupants,
                        "roommate_name": roommate_name
                    }
                    print(f"DEBUG: Vendor data added: {allocation_data['vendor_accommodation']}")
                else:
                    print(f"DEBUG: Vendor not found for vendor_id: {allocation.vendor_accommodation_id}")
            
            # Get event data
            if allocation.event_id:
                print(f"DEBUG: Fetching event data for event_id: {allocation.event_id}")
                event = db.query(Event).filter(Event.id == allocation.event_id).first()
                if event:
                    allocation_data["event"] = {
                        "title": event.title
                    }
                    print(f"DEBUG: Event data added: {allocation_data['event']}")
                else:
                    print(f"DEBUG: Event not found for event_id: {allocation.event_id}")
            
            # Get participant data with gender from registration
            if allocation.participant_id:
                print(f"DEBUG: Fetching participant data for participant_id: {allocation.participant_id}")
                participant = db.query(EventParticipant).filter(
                    EventParticipant.id == allocation.participant_id
                ).first()
                if participant:
                    # Get gender from public_registrations table
                    from sqlalchemy import text
                    gender_result = db.execute(text(
                        "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                    ), {"participant_id": allocation.participant_id}).fetchone()
                    
                    gender = None
                    if gender_result and gender_result[0]:
                        # Convert registration format to standard format
                        reg_gender = gender_result[0].lower()
                        if reg_gender in ['man', 'male']:
                            gender = 'male'
                        elif reg_gender in ['woman', 'female']:
                            gender = 'female'
                        else:
                            gender = 'other'
                    
                    allocation_data["participant"] = {
                        "name": participant.full_name,
                        "role": participant.participant_role or participant.role,
                        "gender": gender
                    }
                    print(f"DEBUG: Participant data added: {allocation_data['participant']}")
                else:
                    print(f"DEBUG: Participant not found for participant_id: {allocation.participant_id}")
            
            result.append(allocation_data)
            print(f"DEBUG: Completed processing allocation {allocation.id}")
        
        print(f"[HOTEL] DEBUG: Returning {len(result)} processed allocations")
        return result
        
    except Exception as e:
        print(f"[HOTEL] DEBUG: Error in get_allocations: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching allocations: {str(e)}"
        )

@router.get("/allocations/detailed")
def get_detailed_allocations(
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all allocations for tenant with related data"""
    try:
        from app.models.guesthouse import AccommodationAllocation, Room, GuestHouse, VendorAccommodation
        from app.models.event import Event
        from app.models.event_participant import EventParticipant
        from app.models.user import User
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        
        # Build query
        query = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.tenant_id == tenant_id
        )
        
        if event_id:
            query = query.filter(AccommodationAllocation.event_id == event_id)
        
        allocations = query.all()
        
        # Manually build response with related data
        result = []
        for allocation in allocations:
            allocation_data = {
                "id": allocation.id,
                "guest_name": allocation.guest_name or "Unknown Guest",
                "guest_email": allocation.guest_email or "",
                "guest_phone": allocation.guest_phone or "",
                "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else "",
                "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else "",
                "number_of_guests": allocation.number_of_guests or 1,
                "accommodation_type": allocation.accommodation_type or "unknown",
                "status": allocation.status or "booked",
                "room_type": allocation.room_type,  # Include room type
                "room": None,
                "vendor_accommodation": None,
                "event": None,
                "participant": None
            }
            
            # Add room data if exists
            if allocation.room_id:
                room = db.query(Room).filter(Room.id == allocation.room_id).first()
                if room:
                    guesthouse = db.query(GuestHouse).filter(GuestHouse.id == room.guesthouse_id).first()
                    allocation_data["room"] = {
                        "id": room.id,
                        "room_number": room.room_number,
                        "capacity": room.capacity,
                        "current_occupants": room.current_occupants,
                        "guesthouse": {
                            "name": guesthouse.name if guesthouse else "Unknown"
                        }
                    }
            
            # Add vendor data if exists
            if allocation.vendor_accommodation_id:
                vendor = db.query(VendorAccommodation).filter(
                    VendorAccommodation.id == allocation.vendor_accommodation_id
                ).first()
                if vendor:
                    allocation_data["vendor_accommodation"] = {
                        "id": vendor.id,
                        "vendor_name": vendor.vendor_name,
                        "capacity": vendor.capacity,
                        "current_occupants": vendor.current_occupants
                    }
            
            # Add event data if exists
            if allocation.event_id:
                event = db.query(Event).filter(Event.id == allocation.event_id).first()
                if event:
                    allocation_data["event"] = {
                        "title": event.title
                    }
            
            # Add participant data if exists
            if allocation.participant_id:
                participant = db.query(EventParticipant).filter(
                    EventParticipant.id == allocation.participant_id
                ).first()
                if participant:
                    # Get gender from public_registrations table
                    from sqlalchemy import text
                    gender_result = db.execute(text(
                        "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                    ), {"participant_id": allocation.participant_id}).fetchone()
                    
                    gender = None
                    if gender_result and gender_result[0]:
                        # Convert registration format to standard format
                        reg_gender = gender_result[0].lower()
                        if reg_gender in ['man', 'male']:
                            gender = 'male'
                        elif reg_gender in ['woman', 'female']:
                            gender = 'female'
                        else:
                            gender = 'other'
                    
                    allocation_data["participant"] = {
                        "name": participant.full_name,
                        "role": participant.participant_role or participant.role,
                        "gender": gender
                    }
            
            result.append(allocation_data)
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching detailed allocations: {str(e)}"
        )

@router.put("/guesthouses/{guesthouse_id}", response_model=schemas.GuestHouse)
def update_guesthouse(
    guesthouse_id: int,
    guesthouse_in: schemas.GuestHouseUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Update guesthouse"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    guesthouse = crud.guesthouse.get(db, id=guesthouse_id)
    if not guesthouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guesthouse not found"
        )
    
    guesthouse = crud.guesthouse.update(db, db_obj=guesthouse, obj_in=guesthouse_in)
    return guesthouse

@router.delete("/guesthouses/{guesthouse_id}")
def delete_guesthouse(
    guesthouse_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Delete guesthouse"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    guesthouse = crud.guesthouse.get(db, id=guesthouse_id)
    if not guesthouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guesthouse not found"
        )
    
    crud.guesthouse.remove(db, id=guesthouse_id)
    return {"message": "Guesthouse deleted successfully"}

@router.delete("/allocations/{allocation_id}")
def delete_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Delete allocation"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    allocation = crud.accommodation_allocation.get(db, id=allocation_id)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )
    
    # Verify allocation belongs to the tenant
    if allocation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this allocation"
        )
    
    crud.accommodation_allocation.remove(db, id=allocation_id)
    return {"message": "Allocation deleted successfully"}

@router.patch("/allocations/{allocation_id}/status")
def update_allocation_status(
    allocation_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Update allocation status - Admin or self update"""
    from app.models.guesthouse import AccommodationAllocation
    from app.models.event_participant import EventParticipant
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    allocation = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.id == allocation_id
    ).first()
    
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )
    
    if allocation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this allocation"
        )
    
    # Check permissions
    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]
    
    if not is_admin:
        if allocation.participant_id:
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == allocation.participant_id
            ).first()
            
            if not participant or participant.email != current_user.email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own accommodation"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this accommodation"
            )
    
    # Update status
    new_status = status_data.get('status')
    if new_status:
        allocation.status = new_status
        db.commit()
        db.refresh(allocation)
    
    return {"message": "Status updated successfully", "status": allocation.status}

@router.patch("/allocations/{allocation_id}/check-in")
def check_in_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Check in allocation - Admin or self check-in"""
    from app.models.guesthouse import AccommodationAllocation
    from app.models.event_participant import EventParticipant
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    allocation = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.id == allocation_id
    ).first()
    
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )
    
    # Verify allocation belongs to the tenant
    if allocation.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this allocation"
        )
    
    # Check permissions: Admin can check in anyone, regular user can only check in themselves
    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]
    
    if not is_admin:
        # For non-admin users, verify they are checking in their own accommodation
        if allocation.participant_id:
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == allocation.participant_id
            ).first()
            
            if not participant or participant.email != current_user.email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only check in to your own accommodation"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to check in this accommodation"
            )
    
    # Update status to checked_in
    allocation.status = "checked_in"
    db.commit()
    db.refresh(allocation)
    
    return {"message": "Guest checked in successfully", "status": allocation.status}

@router.patch("/allocations/bulk-check-in")
def bulk_check_in_allocations(
    allocation_ids: List[int],
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Bulk check in allocations"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    updated_count = 0
    for allocation_id in allocation_ids:
        allocation = crud.accommodation_allocation.get(db, id=allocation_id)
        if allocation and allocation.tenant_id == tenant_id:
            allocation.status = "checked_in"
            updated_count += 1
    
    db.commit()
    
    return {"message": f"Successfully checked in {updated_count} guests", "updated_count": updated_count}

@router.get("/participant/{participant_id}/accommodation")
def get_participant_accommodation(
    participant_id: int,
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    x_tenant_id: str = Header(None, alias="X-Tenant-ID"),
    x_tenant_context: str = Header(None, alias="X-Tenant-Context"),
) -> Any:
    """Get accommodation details for a specific participant"""
    # Determine tenant context from headers or user
    tenant_context = x_tenant_context or x_tenant_id or current_user.tenant_id
    print(f"[DEBUG] DEBUG: get_participant_accommodation - Participant: {participant_id}, Event: {event_id}, User: {current_user.email}, Role: {current_user.role}, Tenant Context: {tenant_context}")
    print(f"[DEBUG] DEBUG: Headers - X-Tenant-ID: {x_tenant_id}, X-Tenant-Context: {x_tenant_context}")
    
    from app.models.guesthouse import AccommodationAllocation, Room, GuestHouse, VendorAccommodation
    from app.models.event_participant import EventParticipant
    from app.models.event import Event
    
    try:
        # Get tenant_id from the event instead of user context
        tenant_id = None
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                tenant_id = event.tenant_id
                print(f"[DEBUG] DEBUG: Using event's tenant_id: {tenant_id}")
            else:
                print(f"[DEBUG] DEBUG: Event {event_id} not found")
                return []
        else:
            # If no event_id provided, try to get it from tenant context as fallback
            if tenant_context:
                tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
                print(f"[DEBUG] DEBUG: Using fallback tenant_id: {tenant_id}")
            else:
                print(f"[DEBUG] DEBUG: No tenant context available")
                return []
        
        if not tenant_id:
            print(f"[DEBUG] DEBUG: No tenant_id available")
            return []
        
        print(f"[DEBUG] DEBUG: Final tenant_id: {tenant_id}, type: {type(tenant_id)}")
        
        # Get participant's accommodation allocations
        query = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.tenant_id == tenant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        )
        
        # Filter by event if provided
        if event_id:
            query = query.filter(AccommodationAllocation.event_id == event_id)
            print(f"DEBUG: Filtering by event_id: {event_id}")
        
        allocations = query.all()
        
        print(f"DEBUG: Found {len(allocations)} allocations for participant {participant_id}")
        for i, allocation in enumerate(allocations):
            print(f"DEBUG: Allocation {i+1}: ID={allocation.id}, Event ID={allocation.event_id}, Type={allocation.accommodation_type}, Status={allocation.status}")
        
        accommodations = []
        for allocation in allocations:
            if allocation.room_id:
                # Guesthouse accommodation
                room = db.query(Room).filter(Room.id == allocation.room_id).first()
                if room:
                    guesthouse = db.query(GuestHouse).filter(GuestHouse.id == room.guesthouse_id).first()
                    if guesthouse:
                        # Get roommates for shared rooms
                        roommates = []
                        facilities = []
                        if room.capacity > 1:
                            # Get other allocations for this room
                            other_allocations = db.query(AccommodationAllocation).filter(
                                AccommodationAllocation.room_id == room.id,
                                AccommodationAllocation.id != allocation.id,
                                AccommodationAllocation.status.in_(["booked", "checked_in"])
                            ).all()
                            
                            for other_alloc in other_allocations:
                                if other_alloc.participant_id:
                                    participant = db.query(EventParticipant).filter(
                                        EventParticipant.id == other_alloc.participant_id
                                    ).first()
                                    if participant:
                                        # Get gender from registration
                                        gender_result = db.execute(text(
                                            "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                                        ), {"participant_id": other_alloc.participant_id}).fetchone()
                                        
                                        gender = None
                                        if gender_result and gender_result[0]:
                                            reg_gender = gender_result[0].lower()
                                            if reg_gender in ['man', 'male']:
                                                gender = 'male'
                                            elif reg_gender in ['woman', 'female']:
                                                gender = 'female'
                                            else:
                                                gender = 'other'
                                        
                                        roommates.append({
                                            "name": participant.full_name,
                                            "role": participant.role,
                                            "gender": gender
                                        })
                        
                        # Get guesthouse facilities
                        facilities = []
                        if hasattr(guesthouse, 'facilities') and guesthouse.facilities:
                            if isinstance(guesthouse.facilities, str):
                                try:
                                    import json
                                    parsed_facilities = json.loads(guesthouse.facilities)
                                    if isinstance(parsed_facilities, dict):
                                        facilities = [key for key, value in parsed_facilities.items() if value]
                                    else:
                                        facilities = parsed_facilities
                                except (json.JSONDecodeError, ValueError):
                                    facilities = [f.strip() for f in guesthouse.facilities.split(',') if f.strip()]
                            elif isinstance(guesthouse.facilities, list):
                                facilities = guesthouse.facilities
                            elif isinstance(guesthouse.facilities, dict):
                                facilities = [key for key, value in guesthouse.facilities.items() if value]
                        
                        # Get room-specific facilities
                        room_facilities = []
                        if hasattr(room, 'amenities') and room.amenities:
                            if isinstance(room.amenities, str):
                                try:
                                    import json
                                    parsed_amenities = json.loads(room.amenities)
                                    if isinstance(parsed_amenities, dict):
                                        room_facilities = [key for key, value in parsed_amenities.items() if value]
                                    else:
                                        room_facilities = parsed_amenities
                                except (json.JSONDecodeError, ValueError):
                                    room_facilities = [f.strip() for f in room.amenities.split(',') if f.strip()]
                            elif isinstance(room.amenities, list):
                                room_facilities = room.amenities
                            elif isinstance(room.amenities, dict):
                                room_facilities = [key for key, value in room.amenities.items() if value]
                        
                        # Combine guesthouse and room facilities safely
                        all_facilities = []
                        if isinstance(facilities, list):
                            all_facilities.extend(facilities)
                        elif isinstance(facilities, dict):
                            # Handle case where facilities is a dict - use keys where value is True
                            all_facilities.extend([key for key, value in facilities.items() if value])
                        
                        if isinstance(room_facilities, list):
                            all_facilities.extend(room_facilities)
                        elif isinstance(room_facilities, dict):
                            # Handle case where room_facilities is a dict - use keys where value is True
                            all_facilities.extend([key for key, value in room_facilities.items() if value])
                        
                        accommodations.append({
                            "allocation_id": allocation.id,
                            "type": "guesthouse",
                            "name": f"{guesthouse.name} - Room {room.room_number}",
                            "location": guesthouse.location or guesthouse.name,
                            "address": guesthouse.location or guesthouse.name,
                            "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                            "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None,
                            "status": allocation.status,
                            "room_capacity": room.capacity,
                            "room_occupants": room.current_occupants,
                            "is_shared": room.capacity > 1,
                            "room_number": room.room_number,
                            "description": getattr(guesthouse, 'description', None),
                            "facilities": all_facilities,
                            "room_facilities": room_facilities,
                            "roommates": roommates
                        })
            elif allocation.vendor_accommodation_id:
                # Vendor accommodation
                vendor = db.query(VendorAccommodation).filter(
                    VendorAccommodation.id == allocation.vendor_accommodation_id
                ).first()
                if vendor:
                    # Get roommates for shared vendor rooms
                    roommates = []
                    if allocation.room_type == "double":
                        # Find other allocations for the same vendor with double room type
                        other_allocations = db.query(AccommodationAllocation).filter(
                            AccommodationAllocation.vendor_accommodation_id == vendor.id,
                            AccommodationAllocation.room_type == "double",
                            AccommodationAllocation.id != allocation.id,
                            AccommodationAllocation.status.in_(["booked", "checked_in"])
                        ).all()
                        
                        for other_alloc in other_allocations:
                            if other_alloc.participant_id:
                                participant = db.query(EventParticipant).filter(
                                    EventParticipant.id == other_alloc.participant_id
                                ).first()
                                if participant:
                                    # Get gender from registration
                                    gender_result = db.execute(text(
                                        "SELECT gender_identity FROM public_registrations WHERE participant_id = :participant_id"
                                    ), {"participant_id": other_alloc.participant_id}).fetchone()
                                    
                                    gender = None
                                    if gender_result and gender_result[0]:
                                        reg_gender = gender_result[0].lower()
                                        if reg_gender in ['man', 'male']:
                                            gender = 'male'
                                        elif reg_gender in ['woman', 'female']:
                                            gender = 'female'
                                        else:
                                            gender = 'other'
                                    
                                    roommates.append({
                                        "name": participant.full_name,
                                        "role": participant.role,
                                        "gender": gender
                                    })
                    
                    accommodation_data = {
                        "allocation_id": allocation.id,
                        "type": "vendor",
                        "name": vendor.vendor_name,
                        "location": vendor.location,
                        "address": vendor.location,
                        "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                        "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None,
                        "status": allocation.status,
                        "room_capacity": 2 if allocation.room_type == "double" else 1,
                        "room_occupants": len(roommates) + 1 if allocation.room_type == "double" else 1,
                        "is_shared": allocation.room_type == "double",
                        "room_type": allocation.room_type,
                        "vendor_name": vendor.vendor_name,
                        "vendor_contact": vendor.contact_phone,
                        "description": vendor.description,
                        "roommates": roommates
                    }
                    print(f"DEBUG: Adding vendor accommodation: {accommodation_data}")
                    accommodations.append(accommodation_data)
        
        print(f"[DEBUG] DEBUG: Returning {len(accommodations)} accommodation details")
        for i, acc in enumerate(accommodations):
            print(f"[DEBUG] DEBUG: Accommodation {i+1}: {acc['type']} - {acc['name']} - Status: {acc['status']}")
        return accommodations
        
    except Exception as e:
        print(f"[DEBUG] DEBUG: Error in get_participant_accommodation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching participant accommodation: {str(e)}"
        )

@router.put("/vendor-event-setup/{setup_id}", response_model=schemas.VendorEventAccommodation)
def update_vendor_event_setup(
    setup_id: int,
    setup_data: schemas.VendorEventAccommodationUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Update event-specific accommodation setup for vendor hotel"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    from app.models.guesthouse import VendorEventAccommodation
    setup = db.query(VendorEventAccommodation).filter(
        VendorEventAccommodation.id == setup_id,
        VendorEventAccommodation.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event setup not found"
        )
    
    # Check if reducing capacity below current occupants
    if setup_data.single_rooms is not None and setup_data.double_rooms is not None:
        new_capacity = setup_data.single_rooms + (setup_data.double_rooms * 2)
        if new_capacity < setup.current_occupants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce capacity below current occupants ({setup.current_occupants})"
            )
        setup.total_capacity = new_capacity
    
    # Update fields
    if setup_data.single_rooms is not None:
        setup.single_rooms = setup_data.single_rooms
    if setup_data.double_rooms is not None:
        setup.double_rooms = setup_data.double_rooms
    if setup_data.event_name is not None and setup.current_occupants == 0:
        setup.event_name = setup_data.event_name
    if setup_data.is_active is not None:
        setup.is_active = setup_data.is_active
    
    db.commit()
    db.refresh(setup)
    
    return setup

@router.delete("/vendor-event-setup/{setup_id}")
def delete_vendor_event_setup(
    setup_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Delete event-specific accommodation setup for vendor hotel"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    from app.models.guesthouse import VendorEventAccommodation
    setup = db.query(VendorEventAccommodation).filter(
        VendorEventAccommodation.id == setup_id,
        VendorEventAccommodation.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event setup not found"
        )
    
    # Check if setup has current occupants
    if setup.current_occupants > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete setup with current occupants ({setup.current_occupants})"
        )
    
    db.delete(setup)
    db.commit()
    
    return {"message": "Event setup deleted successfully"}
