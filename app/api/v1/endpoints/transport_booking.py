from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.permissions import has_transport_permissions
from app.crud.transport_booking import transport_booking, transport_vendor
from app.models.transport_booking import BookingStatus
from app.schemas.transport_booking import (
    TransportBooking, TransportBookingCreate, TransportBookingUpdate,
    TransportStatusUpdate, TransportStatusUpdateCreate,
    TransportVendor, TransportVendorCreate,
    BookingGroupRequest, BookingGroupResponse, WelcomePackageCheck
)

router = APIRouter()

# Transport Booking Management
@router.post("/bookings/", response_model=TransportBooking)
def create_transport_booking(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new transport booking"""
    print(f"DEBUG: Transport booking creation - User: {current_user.email}, Role: {current_user.role}")
    
    if not has_transport_permissions(current_user, db):
        print(f"DEBUG: Authorization failed - User does not have transport permissions")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Extract pooling information
    pool_with_booking_ids = request_data.pop("pool_with_booking_ids", [])
    
    # Create booking object from remaining data
    try:
        booking = TransportBookingCreate(**request_data)
    except Exception as e:
        print(f"DEBUG: Error creating booking object: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid booking data: {str(e)}")
    
    if pool_with_booking_ids:
        # Pool with existing bookings
        from app.models.transport_booking import TransportBooking
        
        # Get the first existing booking to merge with
        existing_booking = db.query(TransportBooking).filter(
            TransportBooking.id == pool_with_booking_ids[0],
            TransportBooking.status == "pending"
        ).first()
        
        if not existing_booking:
            raise HTTPException(status_code=400, detail="Existing booking not found or not pending")
        
        # Add new participants to existing booking
        existing_participants = list(existing_booking.participant_ids)
        existing_participants.extend(booking.participant_ids)
        existing_booking.participant_ids = existing_participants
        
        # Update welcome package status if new booking has package
        if booking.has_welcome_package and not existing_booking.has_welcome_package:
            existing_booking.has_welcome_package = True
            existing_booking.package_pickup_location = booking.package_pickup_location or "MSF Office"
        
        db.commit()
        db.refresh(existing_booking)
        
        # Return the updated existing booking with participant details
        return transport_booking.get_booking(db, existing_booking.id)
    else:
        # Create new booking normally
        print(f"DEBUG: Authorization passed, creating booking")
        return transport_booking.create_booking(db, booking, current_user.email)

@router.get("/bookings/", response_model=List[TransportBooking])
def get_transport_bookings(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    booking_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    participant_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transport bookings with filters"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    bookings = transport_booking.get_bookings(
        db, skip=skip, limit=limit, status=status, 
        booking_type=booking_type, date_from=date_from, date_to=date_to
    )
    
    # Filter by participant_id if provided
    if participant_id:
        bookings = [b for b in bookings if participant_id in (b.participant_ids or [])]
    
    # Filter by event_id if provided
    if event_id:
        from app.models.event_participant import EventParticipant
        # Get all participants for this event
        event_participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id
        ).all()
        event_participant_ids = [p.id for p in event_participants]
        
        # Filter bookings that have any participants from this event
        bookings = [
            b for b in bookings 
            if any(pid in event_participant_ids for pid in (b.participant_ids or []))
        ]
    
    return bookings

@router.get("/bookings/{booking_id}", response_model=TransportBooking)
def get_transport_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific transport booking"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return booking

@router.put("/bookings/{booking_id}", response_model=TransportBooking)
def update_transport_booking(
    booking_id: int,
    booking_update: TransportBookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update transport booking"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    booking = transport_booking.update_booking(db, booking_id, booking_update, current_user.email)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return booking

@router.delete("/bookings/{booking_id}")
def delete_transport_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete transport booking (only if not confirmed)"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    print(f"DEBUG: Attempting to delete booking {booking_id} with status: {booking.status} (type: {type(booking.status)})")
    
    # Handle both string and enum comparisons
    if hasattr(booking.status, 'value'):
        status_value = booking.status.value
    else:
        status_value = str(booking.status)
    
    print(f"DEBUG: Status value: '{status_value}'")
    
    if status_value != "pending" and booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot delete booking with status '{status_value}'. Only pending bookings can be deleted.")
    
    success = transport_booking.delete_booking(db, booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": "Booking deleted successfully"}

@router.post("/bookings/{booking_id}/status", response_model=TransportStatusUpdate)
def update_booking_status(
    booking_id: int,
    status_update: TransportStatusUpdateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update booking status (for drivers and admins)"""
    # Allow drivers to update status too (they can be identified by email or special role)
    if not has_transport_permissions(current_user, db):
        # Check if this is a driver for this specific booking
        booking = transport_booking.get_booking(db, booking_id)
        if not booking or booking.driver_email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return transport_booking.add_status_update(db, booking_id, status_update, current_user.email)

@router.get("/bookings/{booking_id}/status", response_model=List[TransportStatusUpdate])
def get_booking_status_history(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get booking status history"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return transport_booking.get_status_updates(db, booking_id)

# Welcome Package Integration
@router.post("/bookings/check-packages", response_model=List[WelcomePackageCheck])
def check_welcome_packages(
    participant_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if participants have welcome packages"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    package_checks = transport_booking.check_welcome_packages(db, participant_ids)
    return [
        WelcomePackageCheck(
            participant_id=check["participant_id"],
            has_package=check["has_package"],
            package_items=check["package_items"]
        )
        for check in package_checks
    ]

# Booking Group Suggestions
@router.post("/bookings/suggest-groups", response_model=BookingGroupResponse)
def suggest_booking_groups(
    request: BookingGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Suggest booking groups based on accommodation and other factors"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    suggestions = transport_booking.suggest_booking_groups(
        db, 
        event_id=request.event_id,
        booking_type=request.booking_type,
        max_passengers=request.max_passengers_per_booking
    )
    
    return BookingGroupResponse(**suggestions)

# Vendor Management
@router.post("/vendors/", response_model=TransportVendor)
def create_transport_vendor(
    vendor: TransportVendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create transport vendor"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return transport_vendor.create_vendor(db, vendor, current_user.email)

@router.get("/vendors/", response_model=List[TransportVendor])
def get_transport_vendors(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transport vendors"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return transport_vendor.get_vendors(db, active_only)

@router.get("/vendors/{vendor_id}", response_model=TransportVendor)
def get_transport_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific transport vendor"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    vendor = transport_vendor.get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return vendor

# Driver Mobile App Endpoints
@router.get("/my-bookings/", response_model=List[TransportBooking])
def get_my_driver_bookings(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get bookings assigned to current driver"""
    # Get bookings where driver_email matches current user
    bookings = transport_booking.get_bookings(db, status=status, date_from=date_from, date_to=date_to)
    
    # Filter to only bookings assigned to this driver
    my_bookings = [
        booking for booking in bookings 
        if booking.driver_email == current_user.email
    ]
    
    return my_bookings

@router.post("/my-bookings/{booking_id}/collect-package")
def collect_package(
    booking_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Driver confirms package collection"""
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.driver_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    if not booking.has_welcome_package:
        raise HTTPException(status_code=400, detail="No package to collect for this booking")
    
    transport_booking.add_status_update(
        db,
        booking_id,
        TransportStatusUpdateCreate(
            status="package_collected",
            notes=notes or "Package collected from MSF Office",
            location=booking.package_pickup_location
        ),
        current_user.email
    )
    
    return {"message": "Package collection confirmed"}

@router.post("/my-bookings/{booking_id}/pickup-visitor")
def pickup_visitor(
    booking_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Driver confirms visitor pickup"""
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.driver_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    transport_booking.add_status_update(
        db,
        booking_id,
        TransportStatusUpdateCreate(
            status="visitor_picked_up",
            notes=notes or "Visitor picked up",
            location="Airport" if booking.booking_type == "airport_pickup" else "Pickup location"
        ),
        current_user.email
    )
    
    return {"message": "Visitor pickup confirmed"}

@router.post("/my-bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Driver completes booking"""
    booking = transport_booking.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.driver_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    transport_booking.add_status_update(
        db,
        booking_id,
        TransportStatusUpdateCreate(
            status="completed",
            notes=notes or "Trip completed",
            location=booking.destination
        ),
        current_user.email
    )
    
    return {"message": "Booking completed"}

@router.post("/bookings/suggest-pooling")
def suggest_pooling(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Suggest pooling opportunities for a new booking"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pickup_location = request.get("pickup_location")
    scheduled_time = request.get("scheduled_time")
    time_window_minutes = request.get("time_window_minutes", 60)
    booking_type = request.get("booking_type", "airport_pickup")
    
    if not pickup_location or not scheduled_time:
        return {"can_pool": False, "existing_bookings": []}
    
    # Find existing bookings from same location within time window
    from datetime import datetime, timedelta
    from app.models.transport_booking import TransportBooking
    from app.models.event_participant import EventParticipant
    
    try:
        if isinstance(scheduled_time, str):
            scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        else:
            scheduled_dt = scheduled_time
    except:
        return {"can_pool": False, "existing_bookings": []}
    
    time_window = timedelta(minutes=time_window_minutes)
    
    existing_bookings = db.query(TransportBooking).filter(
        TransportBooking.booking_type == booking_type,
        TransportBooking.status == "pending",
        TransportBooking.scheduled_time.between(
            scheduled_dt - time_window,
            scheduled_dt + time_window
        )
    ).all()
    
    # Filter by same pickup location
    matching_bookings = []
    for booking in existing_bookings:
        if pickup_location in booking.pickup_locations:
            # Get participant details
            participants = db.query(EventParticipant).filter(
                EventParticipant.id.in_(booking.participant_ids)
            ).all()
            
            booking_data = {
                "id": booking.id,
                "scheduled_time": booking.scheduled_time.isoformat(),
                "arrival_time": booking.arrival_time.isoformat() if booking.arrival_time else None,
                "participants": [{
                    "id": p.id,
                    "name": p.full_name,
                    "email": p.email
                } for p in participants]
            }
            matching_bookings.append(booking_data)
    
    return {
        "can_pool": len(matching_bookings) > 0,
        "existing_bookings": matching_bookings,
        "pickup_location": pickup_location,
        "time_window_minutes": time_window_minutes
    }

@router.post("/bookings/pool")
def pool_bookings(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pool multiple bookings into one"""
    if not has_transport_permissions(current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    booking_ids = request.get("booking_ids", [])
    if len(booking_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 bookings required for pooling")
    
    # Get all bookings
    bookings = db.query(TransportBooking).filter(
        TransportBooking.id.in_(booking_ids),
        TransportBooking.status == "pending"
    ).all()
    
    if len(bookings) != len(booking_ids):
        raise HTTPException(status_code=400, detail="Some bookings not found or not pending")
    
    # Use the first booking as the main one and merge others into it
    main_booking = bookings[0]
    other_bookings = bookings[1:]
    
    # Merge participant IDs
    all_participant_ids = list(main_booking.participant_ids)
    for booking in other_bookings:
        all_participant_ids.extend(booking.participant_ids)
    
    main_booking.participant_ids = all_participant_ids
    
    # Delete the other bookings
    for booking in other_bookings:
        # Delete related status updates
        db.query(TransportStatusUpdate).filter(
            TransportStatusUpdate.booking_id == booking.id
        ).delete()
        db.delete(booking)
    
    db.commit()
    db.refresh(main_booking)
    
    return {"message": "Bookings pooled successfully", "main_booking_id": main_booking.id}