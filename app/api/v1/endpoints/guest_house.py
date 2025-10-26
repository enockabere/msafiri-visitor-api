from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.permissions import has_accommodation_permissions
from app.crud.guest_house import guest_house_crud, guest_house_room_crud, guest_house_booking_crud
from app.schemas.guest_house import (
    GuestHouse, GuestHouseCreate, GuestHouseUpdate,
    GuestHouseRoom, GuestHouseRoomCreate, GuestHouseRoomUpdate,
    GuestHouseBooking, GuestHouseBookingCreate, GuestHouseBookingUpdate,
    RoomAvailabilityCheck, RoomAvailabilityResponse,
    BookingConflictCheck, BookingConflictResponse
)

router = APIRouter()

# Guest House Management
@router.post("/", response_model=GuestHouse)
def create_guest_house(
    guest_house: GuestHouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return guest_house_crud.create_guest_house(db, guest_house, current_user.email)

@router.get("/", response_model=List[GuestHouse])
def get_guest_houses(
    tenant_context: str = Query(...),
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all guest houses for a tenant"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return guest_house_crud.get_guest_houses(db, tenant_context, active_only)

@router.get("/{guest_house_id}", response_model=GuestHouse)
def get_guest_house(
    guest_house_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    guest_house = guest_house_crud.get_guest_house(db, guest_house_id)
    if not guest_house:
        raise HTTPException(status_code=404, detail="Guest house not found")
    
    return guest_house

@router.put("/{guest_house_id}", response_model=GuestHouse)
def update_guest_house(
    guest_house_id: int,
    guest_house_update: GuestHouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    guest_house = guest_house_crud.update_guest_house(db, guest_house_id, guest_house_update)
    if not guest_house:
        raise HTTPException(status_code=404, detail="Guest house not found")
    
    return guest_house

@router.delete("/{guest_house_id}")
def delete_guest_house(
    guest_house_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = guest_house_crud.delete_guest_house(db, guest_house_id)
    if not success:
        raise HTTPException(status_code=404, detail="Guest house not found")
    
    return {"message": "Guest house deleted successfully"}

# Room Management
@router.post("/{guest_house_id}/rooms", response_model=GuestHouseRoom)
def create_room(
    guest_house_id: int,
    room_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new room in guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify guest house exists
    guest_house = guest_house_crud.get_guest_house(db, guest_house_id)
    if not guest_house:
        raise HTTPException(status_code=404, detail="Guest house not found")
    
    room_create = GuestHouseRoomCreate(guest_house_id=guest_house_id, **room_data)
    return guest_house_room_crud.create_room(db, room_create, current_user.email)

@router.get("/{guest_house_id}/rooms", response_model=List[GuestHouseRoom])
def get_rooms(
    guest_house_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all rooms in a guest house"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return guest_house_room_crud.get_rooms(db, guest_house_id, active_only)

@router.put("/rooms/{room_id}", response_model=GuestHouseRoom)
def update_room(
    room_id: int,
    room_update: GuestHouseRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update room details"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    room = guest_house_room_crud.update_room(db, room_id, room_update)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return room

# Room Availability
@router.post("/rooms/check-availability", response_model=List[RoomAvailabilityResponse])
def check_room_availability(
    availability_checks: List[RoomAvailabilityCheck],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check availability of multiple rooms"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    results = []
    for check in availability_checks:
        room = guest_house_room_crud.get_room(db, check.room_id)
        if not room:
            continue
        
        is_available = guest_house_room_crud.check_room_availability(
            db, check.room_id, check.check_in_date, check.check_out_date
        )
        
        results.append(RoomAvailabilityResponse(
            room_id=check.room_id,
            room_number=room.room_number,
            is_available=is_available,
            conflicting_bookings=[]  # Could be expanded to show conflicts
        ))
    
    return results

# Booking Management
@router.post("/bookings", response_model=dict)
def create_booking(
    booking: GuestHouseBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new guest house booking"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check room availability
    is_available = guest_house_room_crud.check_room_availability(
        db, booking.room_id, booking.check_in_date, booking.check_out_date
    )
    
    if not is_available:
        raise HTTPException(status_code=400, detail="Room is not available for the selected dates")
    
    # Check participant conflicts
    conflicts = guest_house_booking_crud.check_participant_conflicts(
        db, booking.participant_id, booking.check_in_date, booking.check_out_date
    )
    
    if conflicts["has_conflicts"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Participant has conflicting bookings: {conflicts['conflicting_bookings']}"
        )
    
    created_booking = guest_house_booking_crud.create_booking(db, booking, current_user.email)
    return {"message": "Booking created successfully", "booking_id": created_booking.id}

@router.get("/bookings")
def get_bookings(
    tenant_context: str = Query(...),
    participant_id: Optional[int] = Query(None),
    guest_house_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get guest house bookings with filters"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return guest_house_booking_crud.get_bookings(
        db, tenant_context, participant_id, guest_house_id, status
    )

@router.put("/bookings/{booking_id}")
def update_booking(
    booking_id: int,
    booking_update: GuestHouseBookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update guest house booking"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # If dates are being updated, check availability and conflicts
    if booking_update.check_in_date or booking_update.check_out_date:
        existing_booking = guest_house_booking_crud.get_booking(db, booking_id)
        if not existing_booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        new_check_in = booking_update.check_in_date or existing_booking.check_in_date
        new_check_out = booking_update.check_out_date or existing_booking.check_out_date
        
        # Check room availability (excluding current booking)
        is_available = guest_house_room_crud.check_room_availability(
            db, existing_booking.room_id, new_check_in, new_check_out, booking_id
        )
        
        if not is_available:
            raise HTTPException(status_code=400, detail="Room is not available for the updated dates")
        
        # Check participant conflicts (excluding current booking)
        conflicts = guest_house_booking_crud.check_participant_conflicts(
            db, existing_booking.participant_id, new_check_in, new_check_out, booking_id
        )
        
        if conflicts["has_conflicts"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Participant has conflicting bookings: {conflicts['conflicting_bookings']}"
            )
    
    booking = guest_house_booking_crud.update_booking(db, booking_id, booking_update)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": "Booking updated successfully"}

# Conflict Checking
@router.post("/bookings/check-conflicts", response_model=BookingConflictResponse)
def check_booking_conflicts(
    conflict_check: BookingConflictCheck,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check for booking conflicts for a participant"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    conflicts = guest_house_booking_crud.check_participant_conflicts(
        db, conflict_check.participant_id, conflict_check.check_in_date, conflict_check.check_out_date
    )
    
    return BookingConflictResponse(**conflicts)

# Get participant's first accommodation
@router.get("/participants/{participant_id}/first-accommodation")
def get_participant_first_accommodation(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the earliest accommodation booking for a participant"""
    if not has_accommodation_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    first_accommodation = guest_house_booking_crud.get_participant_first_accommodation(db, participant_id)
    
    if not first_accommodation:
        raise HTTPException(status_code=404, detail="No accommodation bookings found for participant")
    
    return first_accommodation