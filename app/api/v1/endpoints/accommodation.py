from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.tenant import Tenant

def get_tenant_id_from_context(db, tenant_context, current_user):
    """Helper function to get tenant ID from context"""
    if tenant_context.isdigit():
        return int(tenant_context)
    else:
        # Look up tenant by slug
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
        return tenant.id if tenant else current_user.tenant_id

router = APIRouter()

@router.get("/test")
def test_accommodation_endpoint():
    """Test endpoint to verify accommodation router is working"""
    print("🏠 DEBUG: Accommodation test endpoint called")
    return {"message": "Accommodation router is working", "timestamp": "2024-10-15"}

# GuestHouse endpoints
@router.get("/guesthouses", response_model=List[schemas.GuestHouse])
def get_guesthouses(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all guesthouses for tenant"""
    print(f"DEBUG: get_guesthouses - User: {current_user.email}, Role: {current_user.role}, Tenant Context: {tenant_context}")
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    print(f"DEBUG: Resolved tenant_id: {tenant_id}")
    
    guesthouses = crud.guesthouse.get_by_tenant(db, tenant_id=tenant_id)
    print(f"DEBUG: Found {len(guesthouses)} guesthouses for tenant {tenant_id}")
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
@router.post("/room-allocations", response_model=schemas.AccommodationAllocation)
def create_room_allocation(
    allocation_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Allocate visitor to room with gender validation"""
    print(f"🏠 DEBUG: Room allocation request received")
    print(f"🏠 DEBUG: User: {current_user.email}, Tenant: {tenant_context}")
    print(f"🏠 DEBUG: Allocation data: {allocation_data}")
    print(f"🏠 DEBUG: User role: {current_user.role}")
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        print(f"🏠 DEBUG: Permission denied for role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Validate allocation type and room_id
    if allocation_data.get("accommodation_type") == "guesthouse" and not allocation_data.get("room_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room ID is required for guesthouse allocation"
        )
    
    # Check room and validate gender rules for guesthouse
    if allocation_data.get("room_id"):
        room = crud.room.get(db, id=allocation_data["room_id"])
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        # Get participant to check gender
        if allocation_data.get("participant_id"):
            from app.models.event_participant import EventParticipant
            from app.models.user import User
            
            participant = db.query(EventParticipant).filter(EventParticipant.id == allocation_data["participant_id"]).first()
            if not participant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Participant not found"
                )
            
            # Get participant's user to check gender
            user = db.query(User).filter(User.email == participant.email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found for participant"
                )
            
            # Check if user has gender set
            if not user.gender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot book accommodation for users without gender information. Please update your profile."
                )
            
            # Check gender compatibility for shared rooms
            if room.capacity > 1 and room.current_occupants > 0:
                # Get existing allocations for this room
                from app.models.guesthouse import AccommodationAllocation
                existing_allocations = db.query(AccommodationAllocation).filter(
                    AccommodationAllocation.room_id == room.id,
                    AccommodationAllocation.status.in_(["booked", "checked_in"])
                ).all()
                
                if existing_allocations:
                    # Check gender of existing occupants
                    for existing_allocation in existing_allocations:
                        if existing_allocation.participant_id:
                            existing_participant = db.query(EventParticipant).filter(
                                EventParticipant.id == existing_allocation.participant_id
                            ).first()
                            if existing_participant:
                                existing_user = db.query(User).filter(
                                    User.email == existing_participant.email
                                ).first()
                                if existing_user and existing_user.gender:
                                    # Gender compatibility rules
                                    if user.gender == "other":
                                        raise HTTPException(
                                            status_code=status.HTTP_400_BAD_REQUEST,
                                            detail="Users with 'Other' gender cannot share rooms. Please use vendor hotels or single occupancy rooms."
                                        )
                                    if existing_user.gender == "other":
                                        raise HTTPException(
                                            status_code=status.HTTP_400_BAD_REQUEST,
                                            detail="Cannot share room with user who has 'Other' gender."
                                        )
                                    if user.gender != existing_user.gender:
                                        raise HTTPException(
                                            status_code=status.HTTP_400_BAD_REQUEST,
                                            detail=f"Gender mismatch: Cannot assign {user.gender} to room with {existing_user.gender} occupant(s)."
                                        )
            
            # For "other" gender users in multi-capacity rooms, only allow if room is empty
            if user.gender == "other" and room.capacity > 1 and room.current_occupants > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Users with 'Other' gender can only be assigned to empty shared rooms or single occupancy rooms."
                )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    # Convert dict to schema object for CRUD operation
    from app.schemas.accommodation import AccommodationAllocationCreate
    allocation_schema = AccommodationAllocationCreate(**allocation_data)
    
    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_schema, tenant_id=tenant_id, user_id=current_user.id
    )
    return allocation

# Vendor Accommodation endpoints
@router.get("/vendor-accommodations", response_model=List[schemas.VendorAccommodation])
def get_vendor_accommodations(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all vendor accommodations for tenant"""
    print(f"DEBUG: get_vendor_accommodations - User: {current_user.email}, Role: {current_user.role}, Tenant Context: {tenant_context}")
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    print(f"DEBUG: Resolved tenant_id: {tenant_id}")
    
    vendors = crud.vendor_accommodation.get_by_tenant(db, tenant_id=tenant_id)
    print(f"DEBUG: Found {len(vendors)} vendor accommodations for tenant {tenant_id}")
    return vendors

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

@router.post("/vendor-allocations", response_model=schemas.AccommodationAllocation)
def create_vendor_allocation(
    *,
    db: Session = Depends(get_db),
    allocation_in: schemas.AccommodationAllocationCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Allocate visitor to vendor accommodation"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Validate allocation type and vendor_accommodation_id
    if allocation_in.accommodation_type == "vendor" and not allocation_in.vendor_accommodation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor accommodation ID is required for vendor allocation"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    allocation = crud.accommodation_allocation.create_with_tenant(
        db, obj_in=allocation_in, tenant_id=tenant_id, user_id=current_user.id
    )
    return allocation

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
        print(f"DEBUG: Starting get_allocations for tenant_context: {tenant_context}")
        
        from app.models.guesthouse import AccommodationAllocation, Room, GuestHouse, VendorAccommodation
        from app.models.event import Event
        from app.models.event_participant import EventParticipant
        from app.models.user import User
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        print(f"DEBUG: Resolved tenant_id: {tenant_id}")
        
        query = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.tenant_id == tenant_id
        )
        
        if event_id:
            query = query.filter(AccommodationAllocation.event_id == event_id)
            print(f"DEBUG: Filtering by event_id: {event_id}")
        
        allocations = query.all()
        print(f"DEBUG: Found {len(allocations)} allocations")
        
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
                    allocation_data["vendor_accommodation"] = {
                        "id": vendor.id,
                        "vendor_name": vendor.vendor_name,
                        "capacity": vendor.capacity,
                        "current_occupants": vendor.current_occupants
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
            
            # Get participant data with gender
            if allocation.participant_id:
                print(f"DEBUG: Fetching participant data for participant_id: {allocation.participant_id}")
                participant = db.query(EventParticipant).filter(
                    EventParticipant.id == allocation.participant_id
                ).first()
                if participant:
                    user = db.query(User).filter(User.email == participant.email).first()
                    allocation_data["participant"] = {
                        "name": participant.full_name,
                        "role": participant.role,
                        "gender": user.gender if user else None
                    }
                    print(f"DEBUG: Participant data added: {allocation_data['participant']}")
                else:
                    print(f"DEBUG: Participant not found for participant_id: {allocation.participant_id}")
            
            result.append(allocation_data)
            print(f"DEBUG: Completed processing allocation {allocation.id}")
        
        print(f"DEBUG: Returning {len(result)} processed allocations")
        return result
        
    except Exception as e:
        print(f"DEBUG: Error in get_allocations: {str(e)}")
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
                    user = db.query(User).filter(User.email == participant.email).first()
                    allocation_data["participant"] = {
                        "name": participant.name,
                        "role": participant.role,
                        "gender": user.gender if user else None
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

@router.patch("/allocations/{allocation_id}/check-in")
def check_in_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Check in allocation"""
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
            detail="Not authorized to update this allocation"
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
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get accommodation details for a specific participant"""
    print(f"DEBUG: get_participant_accommodation - Participant: {participant_id}, User: {current_user.email}, Role: {current_user.role}, Tenant Context: {tenant_context}")
    
    from app.models.guesthouse import AccommodationAllocation, Room, GuestHouse, VendorAccommodation
    from app.models.event_participant import EventParticipant
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    print(f"DEBUG: Resolved tenant_id: {tenant_id}")
    
    # Get participant's accommodation allocations
    allocations = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.participant_id == participant_id,
        AccommodationAllocation.tenant_id == tenant_id,
        AccommodationAllocation.status.in_(["booked", "checked_in"])
    ).all()
    
    print(f"DEBUG: Found {len(allocations)} allocations for participant {participant_id}")
    
    accommodations = []
    for allocation in allocations:
        if allocation.room_id:
            # Guesthouse accommodation
            room = db.query(Room).filter(Room.id == allocation.room_id).first()
            if room:
                guesthouse = db.query(GuestHouse).filter(GuestHouse.id == room.guesthouse_id).first()
                if guesthouse:
                    accommodations.append({
                        "type": "guesthouse",
                        "name": f"{guesthouse.name} - Room {room.room_number}",
                        "location": guesthouse.location or guesthouse.name,
                        "address": guesthouse.location or guesthouse.name,
                        "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                        "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None,
                        "status": allocation.status,
                        "room_capacity": room.capacity,
                        "room_occupants": room.current_occupants,
                        "is_shared": room.capacity > 1
                    })
        elif allocation.vendor_accommodation_id:
            # Vendor accommodation
            vendor = db.query(VendorAccommodation).filter(
                VendorAccommodation.id == allocation.vendor_accommodation_id
            ).first()
            if vendor:
                accommodations.append({
                    "type": "vendor",
                    "name": vendor.vendor_name,
                    "location": vendor.location,
                    "address": vendor.location,
                    "check_in_date": allocation.check_in_date.isoformat() if allocation.check_in_date else None,
                    "check_out_date": allocation.check_out_date.isoformat() if allocation.check_out_date else None,
                    "status": allocation.status,
                    "room_capacity": vendor.capacity,
                    "room_occupants": vendor.current_occupants,
                    "is_shared": vendor.capacity > 1
                })
    
    print(f"DEBUG: Returning {len(accommodations)} accommodation details")
    return accommodations