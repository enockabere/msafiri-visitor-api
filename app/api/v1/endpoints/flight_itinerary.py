from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.flight_itinerary import FlightItinerary
from app.models.event_participant import EventParticipant
from app.models.transport_request import TransportRequest
from app.models.event import Event
from app.models.transport_provider import TransportProvider
from app.models.guesthouse import AccommodationAllocation, VendorAccommodation, Room
from app.models.user import User
from app.models.notification import Notification
from datetime import datetime, timedelta
from app.services.absolute_cabs_service import get_absolute_cabs_service
import math
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/participant/{participant_id}")
def get_participant_flight_itinerary(
    participant_id: int,
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get flight itinerary for a participant"""
    # Get participant email from event participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        return []
    
    # Get flight itineraries for this participant
    itineraries = db.query(FlightItinerary).filter(
        and_(
            FlightItinerary.user_email == participant.email,
            FlightItinerary.event_id == (event_id or participant.event_id)
        )
    ).all()
    
    return [{
        "id": itinerary.id,
        "departure_city": itinerary.departure_city,
        "arrival_city": itinerary.arrival_city,
        "departure_airport": itinerary.departure_airport,
        "arrival_airport": itinerary.arrival_airport,
        "pickup_location": itinerary.pickup_location,
        "departure_date": itinerary.departure_date.isoformat() if itinerary.departure_date else None,
        "departure_time": itinerary.departure_time if itinerary.departure_time else None,
        "arrival_date": itinerary.arrival_date.isoformat() if itinerary.arrival_date else None,
        "arrival_time": itinerary.arrival_time if itinerary.arrival_time else None,
        "airline": itinerary.airline,
        "flight_number": itinerary.flight_number,
        "itinerary_type": itinerary.itinerary_type or "arrival",
        "status": itinerary.status or "pending",
        "destination": itinerary.destination,
        "created_at": itinerary.created_at.isoformat() if itinerary.created_at else None
    } for itinerary in itineraries]

@router.post("/")
def create_flight_itinerary(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    flight_data: dict
) -> Any:
    """Create a new flight itinerary"""
    print(f"DEBUG: Received flight data: {flight_data}")
    print(f"DEBUG: Current user: {current_user.email}")
    
    try:
        # Parse datetime strings
        departure_date = None
        arrival_date = None
        
        if flight_data.get("departure_date"):
            departure_date = datetime.fromisoformat(flight_data["departure_date"].replace('Z', '+00:00'))
            print(f"DEBUG: Parsed departure_date: {departure_date}")
        
        if flight_data.get("arrival_date"):
            arrival_date = datetime.fromisoformat(flight_data["arrival_date"].replace('Z', '+00:00'))
            print(f"DEBUG: Parsed arrival_date: {arrival_date}")
        
        # Create flight itinerary - map mobile app fields to database columns
        itinerary = FlightItinerary(
            event_id=flight_data["event_id"],
            user_email=current_user.email,
            airline=flight_data.get("airline"),
            flight_number=flight_data.get("flight_number"),
            departure_city=flight_data.get("departure_airport"),  # Mobile sends departure_airport
            arrival_city=flight_data.get("arrival_airport"),  # Mobile sends arrival_airport
            departure_airport=flight_data.get("departure_airport"),  # Also store in departure_airport field
            arrival_airport=flight_data.get("arrival_airport"),  # Also store in arrival_airport field
            pickup_location=flight_data.get("pickup_location"),
            departure_date=departure_date,
            arrival_date=arrival_date,
            itinerary_type=flight_data.get("itinerary_type", "arrival"),
            destination=flight_data.get("destination"),
            status="pending"  # Default status
        )
        
        print(f"DEBUG: Created itinerary object: {itinerary.__dict__}")
        
        db.add(itinerary)
        db.commit()
        db.refresh(itinerary)
        
        print(f"DEBUG: Successfully saved itinerary with ID: {itinerary.id}")
        
        return {"id": itinerary.id, "message": "Flight itinerary created successfully"}
        
    except Exception as e:
        print(f"DEBUG: Error creating flight itinerary: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create flight itinerary: {str(e)}"
        )

@router.post("/confirm-itineraries")
def confirm_itineraries(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    itinerary_data: dict
) -> Any:
    """
    Confirm flight itineraries and automatically create/book transport requests.

    This endpoint:
    1. Updates itinerary status to "confirmed"
    2. Updates participant's ticket_document flag
    3. Auto-creates transport requests from confirmed itineraries
    4. Attempts auto-booking with transport provider if configured
    5. Returns comprehensive status including booking results
    """
    itinerary_ids = itinerary_data.get("itinerary_ids", [])
    if not itinerary_ids:
        return {"message": "No itineraries to confirm"}

    # Track which events need participant updates
    event_ids = set()

    # Update all specified itineraries to confirmed
    for itinerary_id in itinerary_ids:
        itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == itinerary_id,
            FlightItinerary.user_email == current_user.email
        ).first()

        if itinerary:
            itinerary.status = "confirmed"
            event_ids.add(itinerary.event_id)

    # Update EventParticipant ticket_document for each event
    for event_id in event_ids:
        participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()

        if participant:
            participant.ticket_document = True

    # Commit itinerary confirmations
    db.commit()

    # Auto-create transport requests for each confirmed itinerary individually
    transport_bookings = []
    for itinerary_id in itinerary_ids:
        try:
            itinerary = db.query(FlightItinerary).filter(
                FlightItinerary.id == itinerary_id,
                FlightItinerary.user_email == current_user.email
            ).first()
            
            if not itinerary:
                continue
                
            # Create transport request for this specific itinerary
            transport_request = create_transport_request_from_itinerary(itinerary, current_user.email, db)
            
            if transport_request:
                # Attempt auto-booking for this single request
                booking_results = attempt_auto_booking(itinerary.event_id, [transport_request], db)
                
                transport_bookings.append({
                    "itinerary_id": itinerary_id,
                    "event_id": itinerary.event_id,
                    "requests_created": 1,
                    "booking_results": booking_results
                })
            else:
                transport_bookings.append({
                    "itinerary_id": itinerary_id,
                    "event_id": itinerary.event_id,
                    "requests_created": 0,
                    "booking_results": [],
                    "error": "Failed to create transport request"
                })
                
        except Exception as e:
            db.rollback()
            transport_bookings.append({
                "itinerary_id": itinerary_id,
                "error": str(e),
                "requests_created": 0,
                "booking_results": []
            })

    # Commit all transport request creations
    try:
        db.commit()
    except Exception as e:
        db.rollback()
    
    # Calculate summary statistics
    total_requests_created = sum(tb.get("requests_created", 0) for tb in transport_bookings)
    total_auto_booked = sum(
        len([r for r in tb.get("booking_results", []) if r.get("auto_booked")])
        for tb in transport_bookings
    )
    total_pooled = sum(
        len([r for r in tb.get("booking_results", []) if r.get("is_pooled")])
        for tb in transport_bookings
    )

    return {
        "message": f"Confirmed {len(itinerary_ids)} itineraries successfully",
        "transport_bookings": transport_bookings,
        "summary": {
            "itineraries_confirmed": len(itinerary_ids),
            "transport_requests_created": total_requests_created,
            "auto_booked": total_auto_booked,
            "pooled_bookings": total_pooled
        }
    }

@router.delete("/cleanup-orphaned-transport/{event_id}")
def cleanup_orphaned_transport(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Clean up orphaned transport requests that have no linked flight itinerary"""
    # Find orphaned transport requests
    orphaned_requests = db.query(TransportRequest).filter(
        TransportRequest.user_email == current_user.email,
        TransportRequest.event_id == event_id,
        TransportRequest.flight_itinerary_id == None
    ).all()
    
    if orphaned_requests:
        for request in orphaned_requests:
            db.delete(request)
        
        db.commit()
        return {"message": f"Cleaned up {len(orphaned_requests)} orphaned transport requests"}
    else:
        return {"message": "No orphaned transport requests found"}

@router.delete("/{itinerary_id}")
def delete_flight_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Delete a flight itinerary"""
    print(f"DEBUG: Deleting itinerary {itinerary_id} for user {current_user.email}")

    # Get the itinerary
    itinerary = db.query(FlightItinerary).filter(
        FlightItinerary.id == itinerary_id
    ).first()

    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight itinerary not found"
        )

    # Check if user owns this itinerary
    if itinerary.user_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this itinerary"
        )

    # Delete all related transport requests
    related_requests = db.query(TransportRequest).filter(
        TransportRequest.flight_itinerary_id == itinerary_id
    ).all()

    if related_requests:
        for request in related_requests:
            db.delete(request)
        db.flush()

    # Delete the itinerary
    db.delete(itinerary)
    db.commit()

    # Also delete any orphaned transport requests for this user/event that have no flight_itinerary_id
    orphaned_requests = db.query(TransportRequest).filter(
        TransportRequest.user_email == current_user.email,
        TransportRequest.event_id == itinerary.event_id,
        TransportRequest.flight_itinerary_id == None
    ).all()
    
    if orphaned_requests:
        for request in orphaned_requests:
            db.delete(request)
    return {"message": "Flight itinerary deleted successfully"}


# ============================================================================
# AUTO-BOOKING HELPER FUNCTIONS
# ============================================================================

def get_participant_accommodation_address(
    user_email: str,
    event_id: int,
    position: str,  # "first" or "last"
    db: Session
) -> Optional[Dict[str, Any]]:
    """
    Get accommodation address for a participant.

    Args:
        user_email: Participant's email
        event_id: Event ID
        position: "first" for arrival destination, "last" for departure pickup
        db: Database session

    Returns:
        Dictionary with address, latitude, longitude, name or None
    """
    try:
        # Get participant
        participant = db.query(EventParticipant).filter(
            EventParticipant.email == user_email,
            EventParticipant.event_id == event_id
        ).first()

        if not participant:
            logger.warning(f"Participant not found for email {user_email} and event {event_id}")
            return None

        # Get accommodation allocations ordered by check-in date
        allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant.id,
            AccommodationAllocation.event_id == event_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).order_by(
            AccommodationAllocation.check_in_date.asc()
        ).all()

        if not allocations:
            logger.info(f"No accommodation allocations found for participant {participant.id}")
            return None

        # Select first or last allocation
        allocation = allocations[0] if position == "first" else allocations[-1]

        # Get vendor accommodation details
        if allocation.vendor_accommodation_id:
            vendor_acc = db.query(VendorAccommodation).filter(
                VendorAccommodation.id == allocation.vendor_accommodation_id
            ).first()

            if vendor_acc and vendor_acc.location:
                return {
                    "address": vendor_acc.location,
                    "latitude": float(vendor_acc.latitude) if vendor_acc.latitude else None,
                    "longitude": float(vendor_acc.longitude) if vendor_acc.longitude else None,
                    "name": vendor_acc.vendor_name
                }

        # Fallback to room allocation if no vendor
        if allocation.room_id:
            room = db.query(Room).filter(Room.id == allocation.room_id).first()
            if room and hasattr(room, 'guesthouse') and room.guesthouse:
                return {
                    "address": room.guesthouse.address if hasattr(room.guesthouse, 'address') else None,
                    "latitude": float(room.guesthouse.latitude) if hasattr(room.guesthouse, 'latitude') and room.guesthouse.latitude else None,
                    "longitude": float(room.guesthouse.longitude) if hasattr(room.guesthouse, 'longitude') and room.guesthouse.longitude else None,
                    "name": room.guesthouse.name if hasattr(room.guesthouse, 'name') else None
                }

        return None
    except Exception as e:
        logger.error(f"Error getting accommodation address: {str(e)}")
        return None


def create_transport_request_from_itinerary(
    itinerary: FlightItinerary,
    user_email: str,
    db: Session
) -> Optional[TransportRequest]:
    """
    Create a TransportRequest from a FlightItinerary.

    Args:
        itinerary: FlightItinerary object
        user_email: User's email
        db: Database session

    Returns:
        Created TransportRequest or None
    """
    try:
        # Get user details
        user = db.query(User).filter(User.email == user_email).first()

        # Get event details for fallback location
        event = db.query(Event).filter(Event.id == itinerary.event_id).first()
        if not event:
            logger.error(f"Event {itinerary.event_id} not found")
            return None

        # Try to get accommodation address
        position = "first" if itinerary.itinerary_type == "arrival" else "last"
        accommodation = get_participant_accommodation_address(user_email, itinerary.event_id, position, db)

        # Prepare addresses and coordinates
        if itinerary.itinerary_type == "arrival":
            pickup_addr = itinerary.arrival_airport or itinerary.arrival_city or itinerary.departure_airport or "Airport"
            pickup_lat = None  # Will be populated from predefined locations
            pickup_lon = None

            # Use accommodation address if available, otherwise event location
            if accommodation and accommodation.get("address"):
                dropoff_addr = accommodation["address"]
                dropoff_lat = accommodation.get("latitude")
                dropoff_lon = accommodation.get("longitude")
            else:
                dropoff_addr = itinerary.destination or event.location or "Event Location"
                dropoff_lat = float(event.latitude) if event.latitude else None
                dropoff_lon = float(event.longitude) if event.longitude else None

            pickup_time = itinerary.arrival_date or itinerary.departure_date
            notes = "Airport pickup for arrival flight (auto-created from itinerary)"

        elif itinerary.itinerary_type == "departure":
            # Use accommodation address if available, otherwise event location
            if accommodation and accommodation.get("address"):
                pickup_addr = accommodation["address"]
                pickup_lat = accommodation.get("latitude")
                pickup_lon = accommodation.get("longitude")
            else:
                pickup_addr = itinerary.pickup_location or itinerary.destination or event.location or "Event Location"
                pickup_lat = float(event.latitude) if event.latitude else None
                pickup_lon = float(event.longitude) if event.longitude else None

            dropoff_addr = itinerary.departure_airport or itinerary.departure_city or "Airport"
            dropoff_lat = None  # Will be populated from predefined locations
            dropoff_lon = None

            # Pickup 2 hours before departure
            if itinerary.departure_date:
                pickup_time = itinerary.departure_date - timedelta(hours=2)
            else:
                logger.warning(f"Departure itinerary {itinerary.id} has no departure_date")
                return None

            notes = "Airport drop-off for departure flight (auto-created from itinerary)"
        else:
            logger.error(f"Unknown itinerary type: {itinerary.itinerary_type}")
            return None

        # Check if transport request already exists for this itinerary
        existing_request = db.query(TransportRequest).filter(
            TransportRequest.flight_itinerary_id == itinerary.id
        ).first()

        if existing_request:
            return existing_request

        # Get phone number from public registration data
        from sqlalchemy import text
        phone_result = db.execute(
            text("""
                SELECT COALESCE(pr.phone_number, '254743332560') as phone_number
                FROM public_registrations pr
                JOIN event_participants ep ON pr.participant_id = ep.id
                WHERE ep.email = :user_email AND ep.event_id = :event_id
                LIMIT 1
            """),
            {"user_email": user_email, "event_id": itinerary.event_id}
        ).fetchone()
        
        phone_number = phone_result[0] if phone_result else None
        
        # Fallback to user profile if not found in registration
        if not phone_number and user and user.phone_number:
            phone_number = user.phone_number
        
        # Final fallback to known phone number
        if not phone_number:
            phone_number = "254743332560"

        # Create transport request
        transport_request = TransportRequest(
            pickup_address=pickup_addr,
            pickup_latitude=pickup_lat,
            pickup_longitude=pickup_lon,
            dropoff_address=dropoff_addr,
            dropoff_latitude=dropoff_lat,
            dropoff_longitude=dropoff_lon,
            pickup_time=pickup_time,
            passenger_name=user.full_name if user and hasattr(user, 'full_name') else user_email.split('@')[0],
            passenger_phone=phone_number or "254700000000",
            passenger_email=user_email,
            vehicle_type="SUV",
            flight_details=f"{itinerary.airline or ''} {itinerary.flight_number or ''}".strip() or "Flight",
            notes=notes,
            event_id=itinerary.event_id,
            flight_itinerary_id=itinerary.id,
            user_email=user_email,
            status="pending"
        )

        db.add(transport_request)
        db.flush()  # Get ID without committing
        return transport_request

    except Exception as e:
        db.rollback()
        return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    km = 6371 * c  # Radius of earth in kilometers
    return km


def find_pooling_candidates(
    transport_requests: List[TransportRequest],
    db: Session
) -> List[List[TransportRequest]]:
    """
    Find groups of transport requests that can be pooled together.

    Args:
        transport_requests: List of transport requests to analyze
        db: Database session

    Returns:
        List of groups, where each group is a list of transport requests that can be pooled
    """
    if len(transport_requests) < 2:
        return []

    groups = []
    processed = set()

    for i, req1 in enumerate(transport_requests):
        if req1.id in processed:
            continue

        # Start a new group
        group = [req1]
        processed.add(req1.id)

        # Find similar requests
        for j, req2 in enumerate(transport_requests[i+1:], start=i+1):
            if req2.id in processed:
                continue

            # Check time proximity (within 30 minutes)
            time_diff = abs((req1.pickup_time - req2.pickup_time).total_seconds() / 60)
            if time_diff > 30:
                continue

            # Check if both have coordinates
            if not all([req1.pickup_latitude, req1.pickup_longitude, req2.pickup_latitude, req2.pickup_longitude]):
                continue

            if not all([req1.dropoff_latitude, req1.dropoff_longitude, req2.dropoff_latitude, req2.dropoff_longitude]):
                continue

            # Check pickup proximity (within 500m)
            pickup_dist = haversine_distance(
                req1.pickup_latitude, req1.pickup_longitude,
                req2.pickup_latitude, req2.pickup_longitude
            )

            if pickup_dist > 0.5:  # 500 meters
                continue

            # Check dropoff proximity (within 500m)
            dropoff_dist = haversine_distance(
                req1.dropoff_latitude, req1.dropoff_longitude,
                req2.dropoff_latitude, req2.dropoff_longitude
            )

            if dropoff_dist > 0.5:  # 500 meters
                continue

            # Requests are poolable!
            group.append(req2)
            processed.add(req2.id)

        # Only add groups with 2+ requests
        if len(group) >= 2:
            groups.append(group)

    return groups


def book_transport_with_provider(
    request_ids: List[int],
    is_pooled: bool,
    db: Session
) -> Dict[str, Any]:
    """
    Book transport requests with Absolute Cabs provider.

    Args:
        request_ids: List of transport request IDs to book
        is_pooled: Whether this is a pooled booking
        db: Database session

    Returns:
        Dictionary with booking results
    """
    try:
        # Get transport requests
        transport_requests = db.query(TransportRequest).filter(
            TransportRequest.id.in_(request_ids)
        ).all()

        if not transport_requests:
            raise ValueError("No transport requests found")

        # Get event and tenant
        event = db.query(Event).filter(Event.id == transport_requests[0].event_id).first()
        if not event:
            raise ValueError("Event not found")

        # Get Absolute Cabs service
        abs_service = get_absolute_cabs_service(event.tenant_id, db)
        if not abs_service:
            raise ValueError("Absolute Cabs service not configured")

        # Populate missing coordinates from predefined locations
        _populate_missing_coordinates(transport_requests, db)

        if is_pooled:
            # Book as pooled request
            return _book_pooled_request(transport_requests, abs_service, db)
        else:
            # Book individually
            return _book_individual_request(transport_requests[0], abs_service, db)

    except Exception as e:
        logger.error(f"Error booking with provider: {str(e)}")
        raise


def _populate_missing_coordinates(transport_requests: List[TransportRequest], db: Session):
    """Populate missing coordinates using predefined location map"""
    # Predefined locations in Nairobi
    location_map = {
        "jkia": (-1.3192, 36.9278),
        "jomo kenyatta": (-1.3192, 36.9278),
        "airport": (-1.3192, 36.9278),
        "westlands": (-1.2673, 36.8073),
        "kilimani": (-1.2885, 36.7824),
        "lavington": (-1.2792, 36.7677),
        "msf office": (-1.2921, 36.8219),
    }

    for req in transport_requests:
        # Populate pickup coordinates
        if not req.pickup_latitude or not req.pickup_longitude:
            for key, (lat, lon) in location_map.items():
                if key in req.pickup_address.lower():
                    req.pickup_latitude = lat
                    req.pickup_longitude = lon
                    break
            else:
                # Default to Nairobi center
                req.pickup_latitude = -1.2921
                req.pickup_longitude = 36.8219

        # Populate dropoff coordinates
        if not req.dropoff_latitude or not req.dropoff_longitude:
            for key, (lat, lon) in location_map.items():
                if key in req.dropoff_address.lower():
                    req.dropoff_latitude = lat
                    req.dropoff_longitude = lon
                    break
            else:
                # Default to Nairobi center
                req.dropoff_latitude = -1.2921
                req.dropoff_longitude = 36.8219


def _book_pooled_request(
    transport_requests: List[TransportRequest],
    abs_service,
    db: Session
) -> Dict[str, Any]:
    """Book multiple transport requests as a pooled booking"""
    # Use earliest pickup time
    earliest_request = min(transport_requests, key=lambda x: x.pickup_time)
    pickup_datetime = earliest_request.pickup_time.strftime("%Y-%m-%d %H:%M")

    # Collect passengers
    passengers = []
    for req in transport_requests:
        phone = req.passenger_phone
        if not phone or phone.strip() == "":
            # Try to get from public registration
            from sqlalchemy import text
            phone_result = db.execute(
                text("""
                    SELECT COALESCE(pr.phone_number, '254700000000') as phone_number
                    FROM public_registrations pr
                    JOIN event_participants ep ON pr.participant_id = ep.id
                    WHERE ep.email = :user_email AND ep.event_id = :event_id
                    LIMIT 1
                """),
                {"user_email": req.user_email, "event_id": req.event_id}
            ).fetchone()
            phone = phone_result[0] if phone_result else f"254700{abs(hash(req.user_email)) % 1000000:06d}"
        
        passengers.append({
            "name": req.passenger_name,
            "phone": phone,
            "email": req.passenger_email or req.user_email
        })

    # Determine vehicle type based on passenger count
    passenger_count = len(passengers)
    if passenger_count <= 4:
        vehicle_type = "Premio"  # Sedan
    elif passenger_count <= 6:
        vehicle_type = "Rav4"  # SUV
    elif passenger_count <= 14:
        vehicle_type = "14 Seater"  # Van
    else:
        vehicle_type = "Bus"

    # Prepare booking data
    booking_data = {
        "vehicle_type": vehicle_type,
        "pickup_address": earliest_request.pickup_address,
        "pickup_latitude": float(earliest_request.pickup_latitude),
        "pickup_longitude": float(earliest_request.pickup_longitude),
        "dropoff_address": earliest_request.dropoff_address,
        "dropoff_latitude": float(earliest_request.dropoff_latitude),
        "dropoff_longitude": float(earliest_request.dropoff_longitude),
        "pickup_time": pickup_datetime,
        "flightdetails": earliest_request.flight_details or "",
        "notes": f"Pooled booking - {len(passengers)} passengers",
        "passengers": passengers,
        "waypoints": []
    }

    # Call Absolute Cabs API
    api_response = abs_service.create_booking(booking_data)
    booking = api_response.get("booking", {})
    booking_ref = booking.get("ref_no") or f"AC{earliest_request.id:06d}"

    # Extract driver and vehicle details
    driver_name = None
    driver_phone = None
    vehicle_number = None

    if "drivers" in booking and booking["drivers"]:
        driver = booking["drivers"][0]
        driver_name = driver.get("name")
        driver_phone = driver.get("telephone")

    if "vehicles" in booking and booking["vehicles"]:
        vehicle = booking["vehicles"][0]
        vehicle_number = vehicle.get("registration")

    # Update all transport requests
    request_ids_json = json.dumps([req.id for req in transport_requests])

    for idx, req in enumerate(transport_requests):
        req.status = "booked"
        req.booking_reference = booking_ref
        req.driver_name = driver_name
        req.driver_phone = driver_phone
        req.vehicle_number = vehicle_number
        req.auto_booked = True
        req.auto_booking_attempted_at = datetime.utcnow()
        req.pooled_with_request_ids = request_ids_json
        req.is_pool_leader = (idx == 0)  # First request is the leader

    db.flush()

    return {
        "success": True,
        "booking_reference": booking_ref,
        "is_pooled": True,
        "request_ids": [req.id for req in transport_requests],
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "vehicle_number": vehicle_number
    }


def _book_individual_request(
    transport_request: TransportRequest,
    abs_service,
    db: Session
) -> Dict[str, Any]:
    """Book a single transport request"""
    pickup_datetime = transport_request.pickup_time.strftime("%Y-%m-%d %H:%M")

    # Get phone number from transport request or registration data
    phone = transport_request.passenger_phone
    if not phone or phone.strip() == "":
        # Try to get from public registration first
        from sqlalchemy import text
        phone_result = db.execute(
            text("""
                SELECT COALESCE(pr.phone_number, '254700000000') as phone_number
                FROM public_registrations pr
                JOIN event_participants ep ON pr.participant_id = ep.id
                WHERE ep.email = :user_email AND ep.event_id = :event_id
                LIMIT 1
            """),
            {"user_email": transport_request.user_email, "event_id": transport_request.event_id}
        ).fetchone()
        
        if phone_result and phone_result[0]:
            phone = phone_result[0]
        else:
            # Fallback to user profile
            user = db.query(User).filter(User.email == transport_request.user_email).first()
            phone = user.phone_number if user and user.phone_number else f"254700{abs(hash(transport_request.user_email)) % 1000000:06d}"

    # Prepare booking data
    booking_data = {
        "vehicle_type": "Rav4",  # Default SUV
        "pickup_address": transport_request.pickup_address,
        "pickup_latitude": float(transport_request.pickup_latitude),
        "pickup_longitude": float(transport_request.pickup_longitude),
        "dropoff_address": transport_request.dropoff_address,
        "dropoff_latitude": float(transport_request.dropoff_latitude),
        "dropoff_longitude": float(transport_request.dropoff_longitude),
        "pickup_time": pickup_datetime,
        "flightdetails": transport_request.flight_details or "",
        "notes": transport_request.notes or "Auto-booked from itinerary confirmation",
        "passengers": [{
            "name": transport_request.passenger_name,
            "phone": phone,
            "email": transport_request.passenger_email or transport_request.user_email
        }],
        "waypoints": []
    }

    # Call Absolute Cabs API
    api_response = abs_service.create_booking(booking_data)
    booking = api_response.get("booking", {})
    booking_ref = booking.get("ref_no") or f"AC{transport_request.id:06d}"

    # Extract driver and vehicle details
    driver_name = None
    driver_phone = None
    vehicle_number = None

    if "drivers" in booking and booking["drivers"]:
        driver = booking["drivers"][0]
        driver_name = driver.get("name")
        driver_phone = driver.get("telephone")

    if "vehicles" in booking and booking["vehicles"]:
        vehicle = booking["vehicles"][0]
        vehicle_number = vehicle.get("registration")

    # Update transport request
    transport_request.status = "booked"
    transport_request.booking_reference = booking_ref
    transport_request.driver_name = driver_name
    transport_request.driver_phone = driver_phone
    transport_request.vehicle_number = vehicle_number
    transport_request.auto_booked = True
    transport_request.auto_booking_attempted_at = datetime.utcnow()
    transport_request.is_pool_leader = True

    db.flush()

    return {
        "success": True,
        "booking_reference": booking_ref,
        "is_pooled": False,
        "request_ids": [transport_request.id],
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "vehicle_number": vehicle_number
    }


def create_admin_notification(
    tenant_id: int,
    title: str,
    message: str,
    action_url: str,
    db: Session
):
    """Create a notification for admins"""
    try:
        notification = Notification(
            tenant_id=tenant_id,
            title=title,
            message=message,
            notification_type="TRANSPORT_BOOKING_REQUIRED",
            priority="HIGH",
            action_url=action_url,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        db.flush()
        logger.info(f"Created admin notification: {title}")
    except Exception as e:
        logger.error(f"Error creating admin notification: {str(e)}")


def attempt_auto_booking(
    event_id: int,
    pending_requests: List[TransportRequest],
    db: Session
) -> List[Dict[str, Any]]:
    """
    Attempt to automatically book transport requests.
    Includes pooling logic.

    Args:
        event_id: Event ID
        pending_requests: List of pending transport requests
        db: Database session

    Returns:
        List of booking results
    """
    results = []

    try:
        # Get event and provider
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")

        provider = db.query(TransportProvider).filter(
            TransportProvider.tenant_id == event.tenant_id,
            TransportProvider.is_enabled == True
        ).first()

        if not provider:
            # Provider not enabled - notify admin
            create_admin_notification(
                tenant_id=event.tenant_id,
                title="Manual Transport Booking Required",
                message=f"{len(pending_requests)} transport request(s) created for event {event.title}. Please assign driver/vehicle.",
                action_url=f"/transport?event_id={event_id}",
                db=db
            )

            for req in pending_requests:
                req.auto_booking_error = "Transport provider not enabled"
                req.auto_booking_attempted_at = datetime.utcnow()
                results.append({
                    "request_id": req.id,
                    "success": False,
                    "auto_booked": False,
                    "error": "Provider not enabled"
                })

            return results

        # Find pooling candidates
        pooling_groups = find_pooling_candidates(pending_requests, db)
        pooled_request_ids = set()

        # Book pooled groups
        for group in pooling_groups:
            try:
                group_ids = [req.id for req in group]
                pooled_request_ids.update(group_ids)

                booking_result = book_transport_with_provider(group_ids, True, db)

                for req_id in group_ids:
                    results.append({
                        "request_id": req_id,
                        "success": True,
                        "auto_booked": True,
                        "is_pooled": True,
                        "booking_reference": booking_result["booking_reference"],
                        "pooled_with": group_ids
                    })

                logger.info(f"Successfully booked pooled group: {group_ids}")

            except Exception as e:
                logger.error(f"Error booking pooled group: {str(e)}")
                for req in group:
                    req.auto_booking_error = str(e)
                    req.auto_booking_attempted_at = datetime.utcnow()
                    results.append({
                        "request_id": req.id,
                        "success": False,
                        "auto_booked": False,
                        "error": str(e)
                    })

        # Book remaining individual requests
        for req in pending_requests:
            if req.id in pooled_request_ids:
                continue

            try:
                booking_result = book_transport_with_provider([req.id], False, db)

                results.append({
                    "request_id": req.id,
                    "success": True,
                    "auto_booked": True,
                    "is_pooled": False,
                    "booking_reference": booking_result["booking_reference"]
                })

                logger.info(f"Successfully booked individual request: {req.id}")

            except Exception as e:
                logger.error(f"Error booking individual request {req.id}: {str(e)}")
                req.auto_booking_error = str(e)
                req.auto_booking_attempted_at = datetime.utcnow()

                results.append({
                    "request_id": req.id,
                    "success": False,
                    "auto_booked": False,
                    "error": str(e)
                })

                # Notify admin of failure
                create_admin_notification(
                    tenant_id=event.tenant_id,
                    title="Transport Booking Failed",
                    message=f"Auto-booking failed for request {req.id}. Error: {str(e)}",
                    action_url=f"/transport?request_id={req.id}",
                    db=db
                )

        return results

    except Exception as e:
        logger.error(f"Error in attempt_auto_booking: {str(e)}")
        # Mark all as failed
        for req in pending_requests:
            req.auto_booking_error = str(e)
            req.auto_booking_attempted_at = datetime.utcnow()
            results.append({
                "request_id": req.id,
                "success": False,
                "auto_booked": False,
                "error": str(e)
            })
        return results


def auto_create_and_book_transport(
    event_id: int,
    user_email: str,
    db: Session
) -> Dict[str, Any]:
    """
    Main orchestration function: Create transport requests from confirmed itineraries
    and attempt automatic booking.

    Args:
        event_id: Event ID
        user_email: User's email
        db: Database session

    Returns:
        Dictionary with creation and booking results
    """
    try:
        # Get confirmed itineraries for this user/event
        confirmed_itineraries = db.query(FlightItinerary).filter(
            FlightItinerary.event_id == event_id,
            FlightItinerary.user_email == user_email,
            FlightItinerary.status == "confirmed"
        ).all()

        logger.info(f"DEBUG: Found {len(confirmed_itineraries)} confirmed itineraries for user {user_email}, event {event_id}")
        for itinerary in confirmed_itineraries:
            logger.info(f"DEBUG: Itinerary {itinerary.id} - Type: {itinerary.itinerary_type}, Status: {itinerary.status}")

        if not confirmed_itineraries:
            return {
                "requests_created": 0,
                "booking_results": [],
                "message": "No confirmed itineraries found"
            }

        # Create transport requests from itineraries
        created_requests = []
        for itinerary in confirmed_itineraries:
            logger.info(f"DEBUG: Processing itinerary {itinerary.id} (type: {itinerary.itinerary_type})")
            
            # Check if request already exists
            existing = db.query(TransportRequest).filter(
                TransportRequest.flight_itinerary_id == itinerary.id
            ).first()

            if not existing:
                logger.info(f"DEBUG: No existing transport request found for itinerary {itinerary.id}, creating new one")
                transport_request = create_transport_request_from_itinerary(itinerary, user_email, db)
                if transport_request:
                    logger.info(f"DEBUG: Successfully created transport request {transport_request.id} for itinerary {itinerary.id}")
                    created_requests.append(transport_request)
                else:
                    logger.warning(f"DEBUG: Failed to create transport request for itinerary {itinerary.id}")
            else:
                logger.info(f"DEBUG: Transport request {existing.id} already exists for itinerary {itinerary.id} (status: {existing.status})")
                if existing.status == "pending":
                    created_requests.append(existing)

        logger.info(f"DEBUG: Total transport requests to process: {len(created_requests)}")
        for req in created_requests:
            logger.info(f"DEBUG: Request {req.id} - Pickup: {req.pickup_address} -> Dropoff: {req.dropoff_address} at {req.pickup_time}")

        if not created_requests:
            return {
                "requests_created": 0,
                "booking_results": [],
                "message": "No new transport requests created (already exist)"
            }

        # Attempt auto-booking
        booking_results = attempt_auto_booking(event_id, created_requests, db)

        # Commit all changes
        db.commit()

        return {
            "requests_created": len(created_requests),
            "booking_results": booking_results,
            "provider_enabled": any(result.get("auto_booked") for result in booking_results)
        }

    except Exception as e:
        logger.error(f"Error in auto_create_and_book_transport: {str(e)}")
        db.rollback()
        return {
            "requests_created": 0,
            "booking_results": [],
            "error": str(e)
        }