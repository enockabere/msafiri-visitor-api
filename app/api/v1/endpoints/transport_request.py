from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.transport_request import TransportRequest
from app.models.flight_itinerary import FlightItinerary
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.transport_provider import TransportProvider
from app.core.deps import get_current_user
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter()

def _get_coordinates_for_address(address: str):
    """Get coordinates for an address using predefined locations"""
    # Common locations in Nairobi with coordinates
    locations = {
        "jomo kenyatta international airport": (-1.3192, 36.9278),
        "jkia": (-1.3192, 36.9278),
        "nbo": (-1.3192, 36.9278),
        "swiss-belinn nairobi": (-1.2921, 36.8219),
        "event location": (-1.2921, 36.8219),  # Default event location
        "nairobi": (-1.2921, 36.8219),
        "westlands": (-1.2681, 36.8119),
        "kilimani": (-1.3004, 36.7898),
        "karen": (-1.3197, 36.7081),
        "gigiri": (-1.2330, 36.8063)
    }
    
    if not address:
        return None
        
    address_lower = address.lower()
    
    # Check for exact matches or partial matches
    for location, coords in locations.items():
        if location in address_lower:
            return coords
    
    return None

class TransportRequestCreate(BaseModel):
    pickup_address: str
    pickup_latitude: float = None
    pickup_longitude: float = None
    dropoff_address: str
    dropoff_latitude: float = None
    dropoff_longitude: float = None
    pickup_time: datetime
    passenger_name: str
    passenger_phone: str
    passenger_email: str = None
    vehicle_type: str = None
    flight_details: str = None
    notes: str = None
    event_id: int
    flight_itinerary_id: int = None

@router.post("/transport-requests")
def create_transport_request(
    request: TransportRequestCreate,
    db: Session = Depends(get_db)
):
    transport_request = TransportRequest(
        pickup_address=request.pickup_address,
        pickup_latitude=request.pickup_latitude,
        pickup_longitude=request.pickup_longitude,
        dropoff_address=request.dropoff_address,
        dropoff_latitude=request.dropoff_latitude,
        dropoff_longitude=request.dropoff_longitude,
        pickup_time=request.pickup_time,
        passenger_name=request.passenger_name,
        passenger_phone=request.passenger_phone,
        passenger_email=request.passenger_email,
        vehicle_type=request.vehicle_type,
        flight_details=request.flight_details,
        notes=request.notes,
        event_id=request.event_id,
        flight_itinerary_id=request.flight_itinerary_id,
        user_email=request.passenger_email or ""
    )
    
    db.add(transport_request)
    db.commit()
    db.refresh(transport_request)
    
    return {"message": "Transport request created successfully", "id": transport_request.id}

@router.get("/transport-requests/tenant/{tenant_id}")
def get_transport_requests_by_tenant(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    from app.models.event import Event
    
    # Get all events for this tenant
    events = db.query(Event).filter(Event.tenant_id == tenant_id).all()
    event_ids = [event.id for event in events]
    
    if not event_ids:
        return []
    
    # Get transport requests for all events of this tenant
    requests = db.query(TransportRequest).filter(
        TransportRequest.event_id.in_(event_ids)
    ).all()
    
    # Create a mapping of event_id to event for quick lookup
    events_map = {event.id: event for event in events}
    
    # Enrich requests with booking details if they have booking references
    enriched_requests = []
    for req in requests:
        request_data = {
            "id": req.id,
            "pickup_address": req.pickup_address,
            "pickup_latitude": req.pickup_latitude,
            "pickup_longitude": req.pickup_longitude,
            "dropoff_address": req.dropoff_address,
            "dropoff_latitude": req.dropoff_latitude,
            "dropoff_longitude": req.dropoff_longitude,
            "pickup_time": req.pickup_time.isoformat() if req.pickup_time else None,
            "passenger_name": req.passenger_name,
            "passenger_phone": req.passenger_phone,
            "passenger_email": req.passenger_email,
            "vehicle_type": req.vehicle_type,
            "flight_details": req.flight_details,
            "notes": req.notes,
            "status": req.status,
            "event_id": req.event_id,
            "flight_itinerary_id": req.flight_itinerary_id,
            "user_email": req.user_email,
            "driver_name": req.driver_name,
            "driver_phone": req.driver_phone,
            "vehicle_number": req.vehicle_number,
            "vehicle_color": req.vehicle_color,
            "booking_reference": req.booking_reference,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            "event": {
                "id": events_map[req.event_id].id,
                "title": events_map[req.event_id].title,
                "tenant_id": events_map[req.event_id].tenant_id
            } if req.event_id in events_map else None
        }
        
        # If request has booking reference but missing driver/vehicle data, fetch from booking details
        if (req.booking_reference and req.status == "booked" and 
            (not req.driver_name or not req.vehicle_number)):
            try:
                from app.services.absolute_cabs_service import get_absolute_cabs_service
                
                abs_service = get_absolute_cabs_service(tenant_id, db)
                if abs_service:
                    booking_details = abs_service.get_booking_details(req.booking_reference)
                    
                    if "booking" in booking_details:
                        booking = booking_details["booking"]
                        
                        # Extract driver details
                        if "drivers" in booking and booking["drivers"]:
                            driver = booking["drivers"][0]
                            request_data["driver_name"] = driver.get("name")
                            request_data["driver_phone"] = driver.get("telephone")
                            
                            # Update the database record
                            req.driver_name = driver.get("name")
                            req.driver_phone = driver.get("telephone")
                        
                        # Extract vehicle details
                        if "vehicles" in booking and booking["vehicles"]:
                            vehicle = booking["vehicles"][0]
                            request_data["vehicle_number"] = vehicle.get("registration")
                            request_data["vehicle_type"] = vehicle.get("name")
                            
                            # Update the database record
                            req.vehicle_number = vehicle.get("registration")
                            req.vehicle_type = vehicle.get("name")
                        
                        # Commit updates to database
                        db.commit()
                        
            except Exception as e:
                pass  # Silently continue if booking details can't be fetched
        
        enriched_requests.append(request_data)
    
    return enriched_requests

@router.get("/transport-requests/event/{event_id}")
def get_transport_requests_by_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = db.query(TransportRequest).filter(
        TransportRequest.event_id == event_id,
        TransportRequest.user_email == current_user.email
    ).all()
    
    # Enrich requests with booking details if they have booking references
    enriched_requests = []
    for req in requests:
        request_data = {
            "id": req.id,
            "pickup_address": req.pickup_address,
            "dropoff_address": req.dropoff_address,
            "pickup_time": req.pickup_time.isoformat() if req.pickup_time else None,
            "passenger_name": req.passenger_name,
            "passenger_phone": req.passenger_phone,
            "passenger_email": req.passenger_email,
            "vehicle_type": req.vehicle_type,
            "flight_details": req.flight_details,
            "notes": req.notes,
            "status": req.status,
            "event_id": req.event_id,
            "flight_itinerary_id": req.flight_itinerary_id,
            "user_email": req.user_email,
            "driver_name": req.driver_name,
            "driver_phone": req.driver_phone,
            "vehicle_number": req.vehicle_number,
            "vehicle_color": req.vehicle_color,
            "booking_reference": req.booking_reference,
            "created_at": req.created_at.isoformat() if req.created_at else None
        }
        
        # If request has booking reference but missing driver/vehicle data, fetch from booking details
        if (req.booking_reference and req.status == "booked" and 
            (not req.driver_name or not req.vehicle_number)):
            try:
                from app.services.absolute_cabs_service import get_absolute_cabs_service
                from app.models.event import Event
                
                # Get event to find tenant
                event = db.query(Event).filter(Event.id == req.event_id).first()
                if event:
                    abs_service = get_absolute_cabs_service(event.tenant_id, db)
                    if abs_service:
                        booking_details = abs_service.get_booking_details(req.booking_reference)
                        
                        if "booking" in booking_details:
                            booking = booking_details["booking"]
                            
                            # Extract driver details
                            if "drivers" in booking and booking["drivers"]:
                                driver = booking["drivers"][0]
                                request_data["driver_name"] = driver.get("name")
                                request_data["driver_phone"] = driver.get("telephone")
                                
                                # Update the database record
                                req.driver_name = driver.get("name")
                                req.driver_phone = driver.get("telephone")
                            
                            # Extract vehicle details
                            if "vehicles" in booking and booking["vehicles"]:
                                vehicle = booking["vehicles"][0]
                                request_data["vehicle_number"] = vehicle.get("registration")
                                request_data["vehicle_type"] = vehicle.get("name")
                                
                                # Update the database record
                                req.vehicle_number = vehicle.get("registration")
                                req.vehicle_type = vehicle.get("name")
                            
                            # Commit updates to database
                            db.commit()
                            
            except Exception as e:
                pass  # Silently continue if booking details can't be fetched
        
        enriched_requests.append(request_data)
    
    return {"transport_requests": enriched_requests}

@router.post("/create-missing-transport-requests/{event_id}")
def create_missing_transport_requests(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create transport requests for confirmed itineraries that don't have them"""
    
    # Get confirmed itineraries without transport requests
    confirmed_itineraries = db.query(FlightItinerary).filter(
        FlightItinerary.event_id == event_id,
        FlightItinerary.user_email == current_user.email,
        FlightItinerary.status == "confirmed"
    ).all()
    
    transport_requests_created = []
    
    for itinerary in confirmed_itineraries:
        # Check if transport request already exists linked to this itinerary
        existing_request = db.query(TransportRequest).filter(
            TransportRequest.flight_itinerary_id == itinerary.id,
            TransportRequest.user_email == current_user.email
        ).first()

        if existing_request:
            print(f"DEBUG: Transport request already exists for itinerary {itinerary.id}, skipping...")
            continue

        # Check for orphaned transport requests (NULL flight_itinerary_id) that match this itinerary
        # This handles cases where itineraries were deleted and recreated
        flight_details_str = f"{itinerary.airline or ''} {itinerary.flight_number or ''}".strip()
        orphaned_request = None

        if flight_details_str:
            # Look for orphaned request with matching flight details and similar timing
            time_window_start = itinerary.departure_date - timedelta(hours=24) if itinerary.departure_date else None
            time_window_end = itinerary.departure_date + timedelta(hours=24) if itinerary.departure_date else None

            if time_window_start and time_window_end:
                orphaned_request = db.query(TransportRequest).filter(
                    TransportRequest.flight_itinerary_id == None,
                    TransportRequest.user_email == current_user.email,
                    TransportRequest.event_id == itinerary.event_id,
                    TransportRequest.flight_details.like(f"%{flight_details_str}%"),
                    TransportRequest.pickup_time >= time_window_start,
                    TransportRequest.pickup_time <= time_window_end
                ).first()

        if orphaned_request:
            # Relink orphaned request to this itinerary instead of creating a duplicate
            print(f"DEBUG: Found orphaned request {orphaned_request.id} matching itinerary {itinerary.id}, relinking...")
            orphaned_request.flight_itinerary_id = itinerary.id
            transport_requests_created.append(f"relinked-{itinerary.itinerary_type}")
            continue

        if itinerary.itinerary_type == "arrival":
            # Use arrival_airport, fall back to arrival_city, then departure fields
            pickup_addr = (itinerary.arrival_airport or
                          itinerary.arrival_city or
                          itinerary.departure_airport or
                          itinerary.departure_city or
                          "Airport")
            dropoff_addr = itinerary.destination or "Event Location"
            pickup_time = itinerary.arrival_date or itinerary.departure_date
            notes = "Airport pickup for arrival flight"

        elif itinerary.itinerary_type == "departure":
            pickup_addr = itinerary.pickup_location or itinerary.destination or "Event Location"
            # Use departure_airport, fall back to departure_city
            dropoff_addr = (itinerary.departure_airport or
                           itinerary.departure_city or
                           "Airport")
            pickup_time = itinerary.departure_date - timedelta(hours=2)
            notes = "Airport drop-off for departure flight"
        else:
            continue

        # Skip if we still don't have valid addresses
        if not pickup_addr or not dropoff_addr:
            print(f"DEBUG: Skipping transport request - missing addresses. Pickup: {pickup_addr}, Dropoff: {dropoff_addr}")
            continue
            
        transport_request = TransportRequest(
            pickup_address=pickup_addr,
            dropoff_address=dropoff_addr,
            pickup_time=pickup_time,
            passenger_name=current_user.full_name,
            passenger_phone=current_user.phone_number or "",
            passenger_email=current_user.email,
            vehicle_type="SUV",
            flight_details=f"{itinerary.airline or ''} {itinerary.flight_number or ''}".strip(),
            notes=notes,
            event_id=itinerary.event_id,
            flight_itinerary_id=itinerary.id,
            user_email=current_user.email,
            status="pending"  # Set to pending initially
        )
        
        db.add(transport_request)
        transport_requests_created.append(itinerary.itinerary_type)
        
        # Create pickup confirmation notification for same day or next day pickups
        pickup_date = pickup_time.date()
        today = datetime.now().date()
        
        if pickup_date <= today + timedelta(days=1):  # Today or tomorrow
            notification = Notification(
                user_email=current_user.email,
                tenant_id=str(itinerary.event_id),
                title="Transport Pickup Confirmation Required",
                message=f"Please confirm your pickup for {itinerary.itinerary_type} transport on {pickup_date.strftime('%B %d')} at {pickup_time.strftime('%H:%M')} from {pickup_addr}.",
                notification_type=NotificationType.PICKUP_CONFIRMATION,
                priority="HIGH",
                send_in_app=True,
                send_push=True,
                action_url=f"/movement?transport_id={transport_request.id}",
                triggered_by="system"
            )
            db.add(notification)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "status": "success",
        "transport_requests_created": transport_requests_created,
        "message": f"Created {len(transport_requests_created)} transport requests"
    }

@router.post("/transport-requests/{request_id}/confirm-pickup")
def confirm_pickup(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm pickup for a transport request - marks as completed"""
    
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.id == request_id,
        TransportRequest.user_email == current_user.email
    ).first()
    
    if not transport_request:
        raise HTTPException(
            status_code=404, 
            detail="Transport request not found"
        )
    
    # Update status to completed when user confirms pickup
    transport_request.status = "completed"
    
    # If there's an associated flight itinerary, mark it as pickup confirmed
    if transport_request.flight_itinerary_id:
        itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == transport_request.flight_itinerary_id
        ).first()
        if itinerary:
            itinerary.pickup_confirmed = True
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Pickup confirmed successfully"
    }

@router.get("/pending-pickup-confirmations")
def get_pending_pickup_confirmations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transport requests that need pickup confirmation for current user"""
    
    now = datetime.now()
    today = now.date()
    
    # Get transport requests that are booked but not pickup confirmed
    # and are scheduled for today or within 2 hours
    pending_requests = db.query(TransportRequest).filter(
        TransportRequest.user_email == current_user.email,
        TransportRequest.status == "booked",
        TransportRequest.pickup_time >= now - timedelta(hours=1),
        TransportRequest.pickup_time <= now + timedelta(hours=2)
    ).all()
    
    result = []
    for req in pending_requests:
        # Check if pickup time is within confirmation window
        time_diff = req.pickup_time - now
        hours_until_pickup = time_diff.total_seconds() / 3600
        
        if -1 <= hours_until_pickup <= 2:  # 1 hour after to 2 hours before
            result.append({
                "id": req.id,
                "pickup_address": req.pickup_address,
                "dropoff_address": req.dropoff_address,
                "pickup_time": req.pickup_time.isoformat(),
                "flight_details": req.flight_details,
                "passenger_name": req.passenger_name,
                "vehicle_type": req.vehicle_type,
                "notes": req.notes,
                "hours_until_pickup": round(hours_until_pickup, 1)
            })
    
    return {"pending_confirmations": result}

@router.post("/transport-requests/{request_id}/book-with-absolute-cabs")
def book_with_absolute_cabs(
    request_id: int,
    db: Session = Depends(get_db)
):
    """Book a transport request with Absolute Cabs"""
    from app.services.absolute_cabs_service import get_absolute_cabs_service
    from app.models.event import Event
    
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.id == request_id
    ).first()
    
    if not transport_request:
        raise HTTPException(
            status_code=404, 
            detail="Transport request not found"
        )
    
    if transport_request.status not in ["pending", "created"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot book request with status: {transport_request.status}"
        )
    
    # Get tenant ID from event
    event = db.query(Event).filter(Event.id == transport_request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get Absolute Cabs service
    absolute_service = get_absolute_cabs_service(event.tenant_id, db)
    if not absolute_service:
        raise HTTPException(
            status_code=400,
            detail="Absolute Cabs not configured for this tenant"
        )
    
    try:
        # Prepare booking data for Absolute Cabs API
        pickup_datetime = transport_request.pickup_time.strftime("%Y-%m-%d %H:%M")
        

        
        # Add coordinates if missing
        if not transport_request.pickup_latitude or not transport_request.pickup_longitude:
            pickup_coords = _get_coordinates_for_address(transport_request.pickup_address)
            if pickup_coords:
                transport_request.pickup_latitude = pickup_coords[0]
                transport_request.pickup_longitude = pickup_coords[1]
        
        if not transport_request.dropoff_latitude or not transport_request.dropoff_longitude:
            dropoff_coords = _get_coordinates_for_address(transport_request.dropoff_address)
            if dropoff_coords:
                transport_request.dropoff_latitude = dropoff_coords[0]
                transport_request.dropoff_longitude = dropoff_coords[1]
        
        # Save coordinates if we added them
        if (transport_request.pickup_latitude or transport_request.dropoff_latitude):
            db.commit()
        
        # Map generic vehicle types to Absolute Cabs specific types
        vehicle_type_mapping = {
            "SUV": "Rav4",
            "SALOON": "Premio",
            "VAN": "14 Seater",
            "BUS": "Bus",
            "SEDAN": "Axio",
            "HATCHBACK": "Fielder"
        }
        
        requested_vehicle = transport_request.vehicle_type or "SUV"
        absolute_vehicle_type = vehicle_type_mapping.get(requested_vehicle, "Rav4")
        
        # Get proper phone number for passenger
        phone_number = transport_request.passenger_phone
        if not phone_number or phone_number.strip() == "":
            from app.models.user import User
            user = db.query(User).filter(User.email == transport_request.user_email).first()
            if user and user.phone_number:
                phone_number = user.phone_number
            else:
                # Use placeholder phone number with request ID for uniqueness
                phone_number = f"254700{transport_request.id:06d}"[-12:]  # Ensure 12 digits max
        
        booking_data = {
            "vehicle_type": absolute_vehicle_type,
            "pickup_address": transport_request.pickup_address,
            "pickup_latitude": float(transport_request.pickup_latitude) if transport_request.pickup_latitude else -1.2921,
            "pickup_longitude": float(transport_request.pickup_longitude) if transport_request.pickup_longitude else 36.8219,
            "dropoff_address": transport_request.dropoff_address,
            "dropoff_latitude": float(transport_request.dropoff_latitude) if transport_request.dropoff_latitude else -1.3192,
            "dropoff_longitude": float(transport_request.dropoff_longitude) if transport_request.dropoff_longitude else 36.9278,
            "pickup_time": pickup_datetime,
            "flightdetails": transport_request.flight_details or "",
            "notes": transport_request.notes or "MSF Event Transport",
            "passengers": [
                {
                    "name": transport_request.passenger_name,
                    "phone": phone_number,
                    "email": transport_request.passenger_email or transport_request.user_email or ""
                }
            ],
            "waypoints": []
        }
        

        
        # Create booking with Absolute Cabs (now returns complete details)
        api_response = absolute_service.create_booking(booking_data)
        
        # Extract booking reference and details from complete response
        booking_ref = None
        booking_details = None
        
        if "booking" in api_response:
            booking_details = api_response["booking"]
            booking_ref = booking_details.get("ref_no")
        elif "ref_no" in api_response:
            booking_ref = api_response["ref_no"]
            booking_details = api_response
        
        # Update transport request with complete booking details
        transport_request.status = "booked"
        transport_request.booking_reference = booking_ref or f"AC{transport_request.id:06d}"
        
        # Extract and store driver details from Absolute Cabs response
        if booking_details and "drivers" in booking_details and booking_details["drivers"]:
            driver = booking_details["drivers"][0]  # Get first assigned driver
            transport_request.driver_name = driver.get("name")
            transport_request.driver_phone = driver.get("telephone")
            # Driver details stored successfully
        
        # Extract and store vehicle details from Absolute Cabs response
        if booking_details and "vehicles" in booking_details and booking_details["vehicles"]:
            vehicle = booking_details["vehicles"][0]  # Get first assigned vehicle
            transport_request.vehicle_number = vehicle.get("registration")
            transport_request.vehicle_type = vehicle.get("name")  # Use actual vehicle name from Absolute Cabs
            # Vehicle details stored successfully
        
        db.commit()
        
        return {
            "success": True,
            "booking_reference": transport_request.booking_reference,
            "message": "Transport request booked successfully with Absolute Cabs",
            "api_response": api_response
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to book with Absolute Cabs: {str(e)}"
        )

class ManualBookingRequest(BaseModel):
    driver_name: str
    driver_phone: str
    vehicle_type: str

@router.post("/transport-requests/{request_id}/manual-booking")
def create_manual_booking(
    request_id: int,
    booking_data: ManualBookingRequest,
    db: Session = Depends(get_db)
):
    """Create a manual transport booking"""
    
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.id == request_id
    ).first()
    
    if not transport_request:
        raise HTTPException(
            status_code=404, 
            detail="Transport request not found"
        )
    
    if transport_request.status not in ["pending", "created"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot book request with status: {transport_request.status}"
        )
    
    try:
        # Update transport request with manual booking details
        transport_request.status = "booked"
        transport_request.notes = f"Manual booking - Driver: {booking_data.driver_name}, Phone: {booking_data.driver_phone}, Vehicle: {booking_data.vehicle_type}"
        
        db.commit()
        
        return {
            "success": True,
            "booking_reference": f"MB{transport_request.id:06d}",
            "message": "Manual transport booking created successfully",
            "driver_name": booking_data.driver_name,
            "driver_phone": booking_data.driver_phone,
            "vehicle_type": booking_data.vehicle_type
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create manual booking: {str(e)}"
        )

class ManualConfirmationRequest(BaseModel):
    driver_name: str
    driver_phone: str
    vehicle_type: str
    vehicle_color: str = None
    number_plate: str

@router.post("/transport-requests/{request_id}/confirm-manual")
def confirm_manual_request(
    request_id: int,
    confirmation_data: ManualConfirmationRequest,
    db: Session = Depends(get_db)
):
    """Confirm a transport request manually with vehicle details"""
    
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.id == request_id
    ).first()
    
    if not transport_request:
        raise HTTPException(
            status_code=404, 
            detail="Transport request not found"
        )
    
    if transport_request.status not in ["pending", "booked", "created"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm request with status: {transport_request.status}"
        )
    
    try:
        # Update transport request with confirmation details
        transport_request.status = "booked"  # Change to booked for mobile app
        transport_request.driver_name = confirmation_data.driver_name
        transport_request.driver_phone = confirmation_data.driver_phone
        transport_request.vehicle_number = confirmation_data.number_plate
        transport_request.vehicle_color = confirmation_data.vehicle_color
        transport_request.vehicle_type = confirmation_data.vehicle_type
        transport_request.booking_reference = f"CR{transport_request.id:06d}"
        
        vehicle_info = f"Driver: {confirmation_data.driver_name}, Phone: {confirmation_data.driver_phone}, Vehicle: {confirmation_data.vehicle_type}"
        if confirmation_data.vehicle_color:
            vehicle_info += f" ({confirmation_data.vehicle_color})"
        vehicle_info += f", Plate: {confirmation_data.number_plate}"
        
        transport_request.notes = f"Confirmed - {vehicle_info}"
        
        db.commit()
        
        return {
            "success": True,
            "confirmation_reference": f"CR{transport_request.id:06d}",
            "message": "Transport request confirmed successfully",
            "driver_name": confirmation_data.driver_name,
            "driver_phone": confirmation_data.driver_phone,
            "vehicle_type": confirmation_data.vehicle_type,
            "vehicle_color": confirmation_data.vehicle_color,
            "number_plate": confirmation_data.number_plate
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm request: {str(e)}"
        )

@router.get("/transport-requests/tenant/{tenant_id}/vehicle-types")
def get_vehicle_types(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get available vehicle types from Absolute Cabs"""
    from app.services.absolute_cabs_service import get_absolute_cabs_service
    
    absolute_service = get_absolute_cabs_service(tenant_id, db)
    if not absolute_service:
        # Return default vehicle types if service not configured
        return {
            "vehicle_types": [
                {"id": 1, "type": "Saloon", "seats": 4},
                {"id": 2, "type": "SUV", "seats": 6},
                {"id": 3, "type": "Van", "seats": 8},
                {"id": 4, "type": "Bus", "seats": 14}
            ]
        }
    
    try:
        vehicle_types = absolute_service.get_vehicle_types()
        return {"vehicle_types": vehicle_types}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch vehicle types: {str(e)}"
        )

class PooledBookingRequest(BaseModel):
    request_ids: List[int]
    vehicle_type: Optional[str] = None  # Auto-selected if not provided
    notes: Optional[str] = None

@router.post("/transport-requests/pool-booking")
def create_pooled_booking(
    pooled_request: PooledBookingRequest,
    db: Session = Depends(get_db)
):
    """Create a pooled booking for multiple transport requests"""
    from app.services.absolute_cabs_service import get_absolute_cabs_service
    from app.models.event import Event
    from app.models.user import User
    
    if len(pooled_request.request_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 requests required for pooling"
        )
    
    # Get all transport requests
    transport_requests = db.query(TransportRequest).filter(
        TransportRequest.id.in_(pooled_request.request_ids)
    ).all()
    
    if len(transport_requests) != len(pooled_request.request_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more transport requests not found"
        )
    
    # Validate all requests are pending/created
    for req in transport_requests:
        if req.status not in ["pending", "created"]:
            raise HTTPException(
                status_code=400,
                detail=f"Request {req.id} has status {req.status}, cannot pool"
            )
    
    # Get tenant ID from first request's event
    event = db.query(Event).filter(Event.id == transport_requests[0].event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get Absolute Cabs service
    absolute_service = get_absolute_cabs_service(event.tenant_id, db)
    if not absolute_service:
        raise HTTPException(
            status_code=400,
            detail="Absolute Cabs not configured for this tenant"
        )
    
    try:
        # Use the earliest pickup time and first pickup location
        earliest_request = min(transport_requests, key=lambda x: x.pickup_time)
        pickup_datetime = earliest_request.pickup_time.strftime("%Y-%m-%d %H:%M")
        
        # Collect all passengers with proper phone numbers
        passengers = []
        flight_details = []
        pickup_times = []
        
        for req in transport_requests:
            # Get user phone number if transport request phone is empty
            phone_number = req.passenger_phone
            if not phone_number or phone_number.strip() == "":
                user = db.query(User).filter(User.email == req.user_email).first()
                if user and user.phone_number:
                    phone_number = user.phone_number
                else:
                    # Use placeholder phone number with request ID for uniqueness
                    phone_number = f"254700{req.id:06d}"[-12:]  # Ensure 12 digits max
            
            passengers.append({
                "name": req.passenger_name,
                "phone": phone_number,
                "email": req.passenger_email or req.user_email or ""
            })
            
            if req.flight_details:
                flight_details.append(req.flight_details)
            
            # Collect pickup times for notes
            pickup_times.append({
                "passenger": req.passenger_name,
                "time": req.pickup_time.strftime("%H:%M")
            })
        
        # Auto-select vehicle type based on passenger count (but allow override)
        if not pooled_request.vehicle_type:
            passenger_count = len(passengers)
            if passenger_count <= 4:
                auto_vehicle = "Premio"  # Sedan for 1-4 passengers
            elif passenger_count <= 6:
                auto_vehicle = "Rav4"    # SUV for 5-6 passengers
            elif passenger_count <= 14:
                auto_vehicle = "14 Seater"  # Van for 7-14 passengers
            else:
                auto_vehicle = "Bus"     # Bus for 15+ passengers
        else:
            # Map generic vehicle types to Absolute Cabs specific types
            vehicle_type_mapping = {
                "SUV": "Rav4",
                "SALOON": "Premio",
                "VAN": "14 Seater",
                "BUS": "Bus",
                "SEDAN": "Axio",
                "HATCHBACK": "Fielder",
                "Premio": "Premio",
                "Rav4": "Rav4",
                "14 Seater": "14 Seater"
            }
            auto_vehicle = vehicle_type_mapping.get(pooled_request.vehicle_type, "Rav4")
        
        # Create waypoints from other dropoff locations
        waypoints = []
        main_dropoff = earliest_request.dropoff_address
        
        for req in transport_requests[1:]:  # Skip the first request (main route)
            if (req.dropoff_address != main_dropoff and 
                req.dropoff_latitude and req.dropoff_longitude):
                waypoints.append({
                    "address": req.dropoff_address,
                    "lat": float(req.dropoff_latitude),
                    "lng": float(req.dropoff_longitude)
                })
        
        # Build comprehensive notes with pickup times
        notes_parts = [f"Pooled booking for {len(passengers)} passengers"]
        
        # Add pickup times if they differ
        unique_times = list(set(pt["time"] for pt in pickup_times))
        if len(unique_times) > 1:
            notes_parts.append("Pickup times:")
            for pt in pickup_times:
                notes_parts.append(f"- {pt['passenger']}: {pt['time']}")
        
        # Add custom notes (but avoid duplicate "Pooled booking from admin portal")
        if pooled_request.notes and "Pooled booking from admin portal" not in pooled_request.notes:
            notes_parts.append(pooled_request.notes)
        
        notes_parts.append("Pooled booking from admin portal")
        
        # Create pooled booking data
        booking_data = {
            "vehicle_type": auto_vehicle,
            "pickup_address": earliest_request.pickup_address,
            "pickup_latitude": float(earliest_request.pickup_latitude) if earliest_request.pickup_latitude else -1.2921,
            "pickup_longitude": float(earliest_request.pickup_longitude) if earliest_request.pickup_longitude else 36.8219,
            "dropoff_address": earliest_request.dropoff_address,
            "dropoff_latitude": float(earliest_request.dropoff_latitude) if earliest_request.dropoff_latitude else -1.3192,
            "dropoff_longitude": float(earliest_request.dropoff_longitude) if earliest_request.dropoff_longitude else 36.9278,
            "pickup_time": pickup_datetime,
            "flightdetails": "; ".join(flight_details) if flight_details else "",
            "notes": "; ".join(notes_parts),
            "passengers": passengers,
            "waypoints": waypoints
        }
        

        
        # Create booking with Absolute Cabs
        api_response = absolute_service.create_booking(booking_data)
        
        # Extract booking reference
        booking_ref = None
        if "booking" in api_response and "ref_no" in api_response["booking"]:
            booking_ref = api_response["booking"]["ref_no"]
        elif "ref_no" in api_response:
            booking_ref = api_response["ref_no"]
        
        # Extract booking details from complete response
        booking_details = None
        if "booking" in api_response:
            booking_details = api_response["booking"]
        elif "drivers" in api_response or "vehicles" in api_response:
            booking_details = api_response
        
        # Update all transport requests with same booking reference and complete details
        shared_ref = booking_ref or f"POOL{earliest_request.id:06d}"
        for req in transport_requests:
            req.status = "booked"
            req.booking_reference = shared_ref
            req.notes = f"Pooled booking - {req.notes or ''}".strip()
            
            # Extract and store driver details from Absolute Cabs response
            if booking_details and "drivers" in booking_details and booking_details["drivers"]:
                driver = booking_details["drivers"][0]  # Get first assigned driver
                req.driver_name = driver.get("name")
                req.driver_phone = driver.get("telephone")
                # Pooled driver details stored successfully
            
            # Extract and store vehicle details from Absolute Cabs response
            if booking_details and "vehicles" in booking_details and booking_details["vehicles"]:
                vehicle = booking_details["vehicles"][0]  # Get first assigned vehicle
                req.vehicle_number = vehicle.get("registration")
                req.vehicle_type = vehicle.get("name")  # Use actual vehicle name from Absolute Cabs
                # Pooled vehicle details stored successfully
        
        db.commit()
        
        return {
            "success": True,
            "booking_reference": shared_ref,
            "pooled_requests": len(transport_requests),
            "passengers": len(passengers),
            "vehicle_type": auto_vehicle,
            "pickup_times": pickup_times,
            "message": f"Successfully created pooled booking for {len(passengers)} passengers with {auto_vehicle}",
            "api_response": api_response
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create pooled booking: {str(e)}"
        )

@router.get("/transport-requests/tenant/{tenant_id}/pooling-suggestions")
def get_pooling_suggestions(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get intelligent pooling suggestions based on time, location, and direction"""
    from app.models.event import Event
    import math
    
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        if not all([lat1, lon1, lat2, lon2]):
            return float('inf')
        
        R = 6371  # Earth's radius in kilometers
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    
    def calculate_bearing(lat1, lon1, lat2, lon2):
        """Calculate bearing between two points"""
        if not all([lat1, lon1, lat2, lon2]):
            return None
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return math.degrees(math.atan2(y, x))
    
    def is_same_direction(req1, req2, bearing_tolerance=45):
        """Check if two requests are going in the same general direction"""
        bearing1 = calculate_bearing(
            req1.pickup_latitude, req1.pickup_longitude,
            req1.dropoff_latitude, req1.dropoff_longitude
        )
        bearing2 = calculate_bearing(
            req2.pickup_latitude, req2.pickup_longitude,
            req2.dropoff_latitude, req2.dropoff_longitude
        )
        
        if bearing1 is None or bearing2 is None:
            return False
        
        # Normalize bearings to 0-360
        bearing1 = (bearing1 + 360) % 360
        bearing2 = (bearing2 + 360) % 360
        
        # Calculate difference
        diff = abs(bearing1 - bearing2)
        if diff > 180:
            diff = 360 - diff
        
        return diff <= bearing_tolerance
    
    def can_be_waypoint(req1, req2):
        """Check if req2 dropoff can be a waypoint for req1's route"""
        if not all([req1.pickup_latitude, req1.pickup_longitude, 
                   req1.dropoff_latitude, req1.dropoff_longitude,
                   req2.dropoff_latitude, req2.dropoff_longitude]):
            return False
        
        # Calculate direct distance from req1 pickup to dropoff
        direct_distance = calculate_distance(
            req1.pickup_latitude, req1.pickup_longitude,
            req1.dropoff_latitude, req1.dropoff_longitude
        )
        
        # Calculate distance via req2's dropoff
        via_distance = (
            calculate_distance(
                req1.pickup_latitude, req1.pickup_longitude,
                req2.dropoff_latitude, req2.dropoff_longitude
            ) +
            calculate_distance(
                req2.dropoff_latitude, req2.dropoff_longitude,
                req1.dropoff_latitude, req1.dropoff_longitude
            )
        )
        
        # Allow up to 30% detour
        return via_distance <= direct_distance * 1.3
    
    # Get all events for this tenant
    events = db.query(Event).filter(Event.tenant_id == tenant_id).all()
    event_ids = [event.id for event in events]
    
    if not event_ids:
        return {"suggestions": []}
    
    # Get pending transport requests (exclude past dates)
    from datetime import datetime
    now = datetime.now()
    
    pending_requests = db.query(TransportRequest).filter(
        TransportRequest.event_id.in_(event_ids),
        TransportRequest.status.in_(["pending", "created"]),
        TransportRequest.pickup_time > now  # Only future requests
    ).all()
    

    
    if len(pending_requests) < 2:
        return {"suggestions": []}
    
    # Ensure all requests have coordinates before pooling analysis
    for req in pending_requests:
        if not req.pickup_latitude or not req.pickup_longitude:
            pickup_coords = _get_coordinates_for_address(req.pickup_address)
            if pickup_coords:
                req.pickup_latitude = pickup_coords[0]
                req.pickup_longitude = pickup_coords[1]
        
        if not req.dropoff_latitude or not req.dropoff_longitude:
            dropoff_coords = _get_coordinates_for_address(req.dropoff_address)
            if dropoff_coords:
                req.dropoff_latitude = dropoff_coords[0]
                req.dropoff_longitude = dropoff_coords[1]
    
    # Commit coordinate updates
    try:
        db.commit()
    except Exception as e:
        db.rollback()
    
    suggestions = []
    processed_requests = set()
    

    
    for i, req1 in enumerate(pending_requests):
        if req1.id in processed_requests:
            continue
        pool_group = [req1]
        waypoints = []
        
        for j, req2 in enumerate(pending_requests):
            if req2.id == req1.id or req2.id in processed_requests:
                continue
            
            # Check time proximity (within 40 minutes)
            time_diff = abs((req1.pickup_time - req2.pickup_time).total_seconds() / 60)
            if time_diff > 40:
                continue
            
            # Check pickup proximity (within 3km)
            pickup_distance = calculate_distance(
                req1.pickup_latitude, req1.pickup_longitude,
                req2.pickup_latitude, req2.pickup_longitude
            )
            
            if pickup_distance == float('inf') or pickup_distance > 3:
                continue
            
            # Check if going to same destination (within 1km)
            dropoff_distance = calculate_distance(
                req1.dropoff_latitude, req1.dropoff_longitude,
                req2.dropoff_latitude, req2.dropoff_longitude
            )
            
            if dropoff_distance <= 1:
                # Same destination - perfect for pooling
                pool_group.append(req2)
                processed_requests.add(req2.id)
            elif is_same_direction(req1, req2) and can_be_waypoint(req1, req2):
                # Same direction and can be waypoint
                pool_group.append(req2)
                waypoints.append({
                    "address": req2.dropoff_address,
                    "lat": req2.dropoff_latitude,
                    "lng": req2.dropoff_longitude,
                    "passenger": req2.passenger_name
                })
                processed_requests.add(req2.id)
        
        # Only suggest if we have 2+ requests in the group
        if len(pool_group) >= 2:
            
            # Calculate final metrics for the group
            final_pickup_distance = 0.0
            final_time_diff = 0.0
            if len(pool_group) > 1:
                # Use the last comparison values
                calculated_distance = calculate_distance(
                    pool_group[0].pickup_latitude, pool_group[0].pickup_longitude,
                    pool_group[-1].pickup_latitude, pool_group[-1].pickup_longitude
                )
                final_pickup_distance = calculated_distance if calculated_distance != float('inf') else 0.0
                final_time_diff = abs((pool_group[0].pickup_time - pool_group[-1].pickup_time).total_seconds() / 60)
            
            suggestions.append({
                "group_id": f"pool_{req1.id}",
                "requests": [
                    {
                        "id": req.id,
                        "passenger_name": req.passenger_name,
                        "pickup_address": req.pickup_address,
                        "dropoff_address": req.dropoff_address,
                        "pickup_time": req.pickup_time.isoformat(),
                        "flight_details": req.flight_details
                    } for req in pool_group
                ],
                "waypoints": waypoints,
                "passenger_count": len(pool_group),
                "time_window": f"{min(req.pickup_time for req in pool_group).strftime('%H:%M')} - {max(req.pickup_time for req in pool_group).strftime('%H:%M')}",
                "suggested_vehicle": "14 Seater" if len(pool_group) > 6 else "Rav4" if len(pool_group) > 4 else "Premio",
                "pickup_distance_km": round(final_pickup_distance, 1),
                "time_diff_minutes": round(final_time_diff, 0)
            })
            
            # Mark all requests in this group as processed
            for req in pool_group:
                processed_requests.add(req.id)
    
    return {"suggestions": suggestions}

@router.get("/transport-feature-flags")
def get_transport_feature_flags():
    """Get transport feature flags for mobile app"""
    return {
        "show_booked_section": False,  # Hide until correct data format is confirmed
        "show_pending_section": True,
        "show_create_request": True
    }

@router.get("/booking-details/{ref_no}")
def get_booking_details(
    ref_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch booking details from transport provider"""
    from app.services.absolute_cabs_service import get_absolute_cabs_service
    from app.models.tenant import Tenant
    
    # Find the transport request to get the event and tenant
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.booking_reference == ref_no,
        TransportRequest.user_email == current_user.email
    ).first()
    
    if not transport_request:
        raise HTTPException(status_code=404, detail=f"Transport request not found for booking reference: {ref_no}")
    
    # Get the event to find the tenant
    from app.models.event import Event
    event = db.query(Event).filter(Event.id == transport_request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found for transport request")
    
    # Get the tenant from the event
    tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found for event")
    
    # Get Absolute Cabs service
    abs_service = get_absolute_cabs_service(tenant.id, db)
    if not abs_service:
        raise HTTPException(status_code=404, detail=f"Transport provider not configured for tenant {tenant.name}")
    
    try:
        booking_details = abs_service.get_booking_details(ref_no)
        
        # Extract the correct format for mobile app
        if "booking" in booking_details:
            booking = booking_details["booking"]
            
            # Extract driver and vehicle details
            driver_name = None
            driver_phone = None
            vehicle_number = None
            vehicle_type = None
            
            if "drivers" in booking and booking["drivers"]:
                driver = booking["drivers"][0]
                driver_name = driver.get("name")
                driver_phone = driver.get("telephone")
            
            if "vehicles" in booking and booking["vehicles"]:
                vehicle = booking["vehicles"][0]
                vehicle_number = vehicle.get("registration")
                vehicle_type = vehicle.get("name")
            
            # Update the transport request with the latest data
            if driver_name or vehicle_number:
                if driver_name:
                    transport_request.driver_name = driver_name
                if driver_phone:
                    transport_request.driver_phone = driver_phone
                if vehicle_number:
                    transport_request.vehicle_number = vehicle_number
                if vehicle_type:
                    transport_request.vehicle_type = vehicle_type
                
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            
            # Return formatted response for mobile app
            response = {
                "success": True,
                "booking_reference": booking.get("ref_no"),
                "status": booking.get("status"),
                "driver_name": driver_name,
                "driver_phone": driver_phone,
                "vehicle_number": vehicle_number,
                "vehicle_type": vehicle_type,
                "pickup_time": booking.get("pickup_time"),
                "pickup_address": booking.get("pickup_address"),
                "dropoff_address": booking.get("dropoff_address"),
                "flight_details": booking.get("flightdetails"),
                "notes": booking.get("notes")
            }
            return response
        else:
            return booking_details
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch booking details: {str(e)}")