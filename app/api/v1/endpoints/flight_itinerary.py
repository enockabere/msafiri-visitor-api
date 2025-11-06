from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.flight_itinerary import FlightItinerary
from app.models.event import Event
from app.models.transport_request import TransportRequest
import requests
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import traceback

router = APIRouter()

class TicketUploadRequest(BaseModel):
    image_data: str  # base64 encoded image
    event_id: int

class ItineraryRequest(BaseModel):
    event_id: int
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    departure_airport: str
    arrival_airport: Optional[str] = None
    departure_date: str  # ISO format
    arrival_date: Optional[str] = None
    itinerary_type: str  # 'arrival', 'departure', 'custom'
    pickup_location: Optional[str] = None
    destination: Optional[str] = None

class ItineraryConfirmRequest(BaseModel):
    itinerary_ids: List[int]

@router.post("/upload-ticket")
async def upload_ticket(
    request: TicketUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload flight ticket for data extraction"""
    
    # Validate image format
    try:
        image_data = base64.b64decode(request.image_data)
        if not (image_data.startswith(b'\xff\xd8\xff') or  # JPEG
                image_data.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
                image_data.startswith(b'GIF87a') or  # GIF87a
                image_data.startswith(b'GIF89a')):  # GIF89a
            raise HTTPException(
                status_code=400,
                detail="Only image files (JPEG, PNG, GIF) are supported"
            )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image data format"
        )
    
    # Verify user is registered for the event
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == request.event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="User not registered for this event"
        )
    
    # Call external ticket processing API (similar to passport)
    try:
        import os
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/extract-ticket-data"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        payload = {
            "image_data": request.image_data
        }
        
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to process ticket image"
            )
        
        result = response.json()
        
        if result.get("result", {}).get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail="Ticket processing failed"
            )
        
        extracted_data = result["result"]["extracted_data"]
        record_id = result["result"]["record_id"]
        
        # Create default itineraries based on extracted data
        event = db.query(Event).filter(Event.id == request.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        itineraries = []
        
        # Create arrival itinerary
        if extracted_data.get("arrival_date") and extracted_data.get("arrival_airport"):
            arrival_itinerary = FlightItinerary(
                event_id=request.event_id,
                user_email=current_user.email,
                airline=extracted_data.get("airline"),
                flight_number=extracted_data.get("flight_number"),
                departure_airport=extracted_data.get("departure_airport", ""),
                arrival_airport=extracted_data.get("arrival_airport"),
                departure_date=datetime.fromisoformat(extracted_data.get("departure_date", extracted_data["arrival_date"])),
                arrival_date=datetime.fromisoformat(extracted_data["arrival_date"]),
                itinerary_type="arrival",
                ticket_record_id=record_id
            )
            db.add(arrival_itinerary)
            itineraries.append("arrival")
        
        # Create departure itinerary (default: day after event ends)
        if event.end_date:
            departure_date = event.end_date + timedelta(days=1)
            departure_itinerary = FlightItinerary(
                event_id=request.event_id,
                user_email=current_user.email,
                departure_airport=extracted_data.get("arrival_airport", ""),
                arrival_airport=extracted_data.get("departure_airport", ""),
                departure_date=departure_date.replace(hour=10, minute=0),
                arrival_date=departure_date.replace(hour=14, minute=0),
                itinerary_type="departure",
                ticket_record_id=record_id
            )
            db.add(departure_itinerary)
            itineraries.append("departure")
        
        db.commit()
        
        return {
            "status": "success",
            "extracted_data": extracted_data,
            "record_id": record_id,
            "created_itineraries": itineraries,
            "message": "Ticket processed and default itineraries created"
        }
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.post("/create-itinerary")
async def create_itinerary(
    request: ItineraryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update flight itinerary"""
    
    # Verify user is registered for the event
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == request.event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="User not registered for this event"
        )
    
    # Validate required fields based on itinerary type
    if request.itinerary_type == "departure":
        if not request.pickup_location:
            raise HTTPException(
                status_code=400,
                detail="Pickup location is required for departure itineraries"
            )
    else:  # arrival or custom
        if not request.arrival_airport or not request.arrival_date:
            raise HTTPException(
                status_code=400,
                detail="Arrival airport and date are required for arrival itineraries"
            )
    
    # Create itinerary
    itinerary = FlightItinerary(
        event_id=request.event_id,
        user_email=current_user.email,
        airline=request.airline,
        flight_number=request.flight_number,
        departure_airport=request.departure_airport,
        arrival_airport=request.arrival_airport,
        departure_date=datetime.fromisoformat(request.departure_date),
        arrival_date=datetime.fromisoformat(request.arrival_date) if request.arrival_date else None,
        itinerary_type=request.itinerary_type,
        pickup_location=request.pickup_location,
        destination=request.destination
    )
    
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)
    
    return {
        "status": "success",
        "itinerary_id": itinerary.id,
        "message": "Itinerary created successfully"
    }

@router.get("/events/{event_id}/itineraries")
async def get_itineraries(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's flight itineraries for an event"""
    
    itineraries = db.query(FlightItinerary).filter(
        FlightItinerary.event_id == event_id,
        FlightItinerary.user_email == current_user.email
    ).all()
    
    return {
        "itineraries": [
            {
                "id": it.id,
                "airline": it.airline,
                "flight_number": it.flight_number,
                "departure_airport": it.departure_airport,
                "arrival_airport": it.arrival_airport,
                "departure_date": it.departure_date.isoformat(),
                "arrival_date": it.arrival_date.isoformat() if it.arrival_date else None,
                "itinerary_type": it.itinerary_type,
                "confirmed": it.confirmed,
                "ticket_record_id": it.ticket_record_id,
                "pickup_location": it.pickup_location,
                "destination": it.destination
            }
            for it in itineraries
        ]
    }

@router.put("/itinerary/{itinerary_id}")
async def update_itinerary(
    itinerary_id: int,
    request: ItineraryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update flight itinerary"""
    
    itinerary = db.query(FlightItinerary).filter(
        FlightItinerary.id == itinerary_id,
        FlightItinerary.user_email == current_user.email
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=404,
            detail="Itinerary not found"
        )
    
    # Validate required fields based on itinerary type
    if request.itinerary_type == "departure":
        if not request.pickup_location:
            raise HTTPException(
                status_code=400,
                detail="Pickup location is required for departure itineraries"
            )
    else:  # arrival or custom
        if not request.arrival_airport or not request.arrival_date:
            raise HTTPException(
                status_code=400,
                detail="Arrival airport and date are required for arrival itineraries"
            )
    
    # Update fields
    itinerary.airline = request.airline
    itinerary.flight_number = request.flight_number
    itinerary.departure_airport = request.departure_airport
    itinerary.arrival_airport = request.arrival_airport
    itinerary.departure_date = datetime.fromisoformat(request.departure_date)
    itinerary.arrival_date = datetime.fromisoformat(request.arrival_date) if request.arrival_date else None
    itinerary.itinerary_type = request.itinerary_type
    itinerary.pickup_location = request.pickup_location
    itinerary.destination = request.destination
    
    # Update corresponding transport request if it exists
    transport_request = db.query(TransportRequest).filter(
        TransportRequest.flight_itinerary_id == itinerary_id,
        TransportRequest.user_email == current_user.email
    ).first()
    
    if transport_request:
        print(f"DEBUG API: Updating transport request for itinerary {itinerary_id}")
        
        if itinerary.itinerary_type == "arrival":
            transport_request.pickup_address = itinerary.arrival_airport or itinerary.departure_airport
            transport_request.dropoff_address = itinerary.destination or "Event Location"
            transport_request.pickup_time = itinerary.arrival_date or itinerary.departure_date
        elif itinerary.itinerary_type == "departure":
            transport_request.pickup_address = itinerary.pickup_location or "Event Location"
            transport_request.dropoff_address = itinerary.departure_airport
            transport_request.pickup_time = itinerary.departure_date - timedelta(hours=2)
            
        transport_request.flight_details = f"{itinerary.airline or ''} {itinerary.flight_number or ''}".strip()
        print(f"DEBUG API: Updated transport request addresses and times")
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Itinerary updated successfully"
    }

@router.post("/confirm-itineraries")
async def confirm_itineraries(
    request: ItineraryConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm flight itineraries and mark ticket as complete"""
    
    print(f"DEBUG API: Confirming itineraries: {request.itinerary_ids}")
    transport_requests_created = []
    
    # Update itineraries as confirmed and create transport requests
    for itinerary_id in request.itinerary_ids:
        itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == itinerary_id,
            FlightItinerary.user_email == current_user.email
        ).first()
        
        if itinerary:
            print(f"DEBUG API: Processing itinerary {itinerary_id}, type: {itinerary.itinerary_type}")
            itinerary.confirmed = True
            
            # Create transport request for this itinerary
            if itinerary.itinerary_type == "arrival":
                # For arrival flights: airport to destination
                pickup_addr = itinerary.arrival_airport or itinerary.departure_airport
                dropoff_addr = itinerary.destination or "Event Location"
                pickup_time = itinerary.arrival_date or itinerary.departure_date
                
                print(f"DEBUG API: Creating ARRIVAL transport request:")
                print(f"  - Pickup: {pickup_addr}")
                print(f"  - Dropoff: {dropoff_addr}")
                print(f"  - Time: {pickup_time}")
                print(f"  - Passenger: {current_user.full_name}")
                
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
                    status="created"
                )
                db.add(transport_request)
                transport_requests_created.append("arrival")
                print(f"DEBUG API: Added arrival transport request to DB")
                
            elif itinerary.itinerary_type == "departure":
                # For departure flights: pickup location to airport
                pickup_addr = itinerary.pickup_location or "Event Location"
                dropoff_addr = itinerary.departure_airport
                pickup_time = itinerary.departure_date - timedelta(hours=2)
                
                print(f"DEBUG API: Creating DEPARTURE transport request:")
                print(f"  - Pickup: {pickup_addr}")
                print(f"  - Dropoff: {dropoff_addr}")
                print(f"  - Time: {pickup_time}")
                print(f"  - Passenger: {current_user.full_name}")
                
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
                    status="created"
                )
                db.add(transport_request)
                transport_requests_created.append("departure")
                print(f"DEBUG API: Added departure transport request to DB")
    
    # Update participant ticket status
    if request.itinerary_ids:
        first_itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == request.itinerary_ids[0]
        ).first()
        
        if first_itinerary:
            participant = db.query(EventParticipant).filter(
                EventParticipant.event_id == first_itinerary.event_id,
                EventParticipant.email == current_user.email
            ).first()
            
            if participant:
                participant.ticket_document = True
    
    try:
        db.commit()
        print(f"DEBUG API: Successfully committed {len(transport_requests_created)} transport requests")
    except Exception as e:
        print(f"DEBUG API: Error committing transport requests: {e}")
        db.rollback()
        raise
    
    return {
        "status": "success",
        "message": "Itineraries confirmed and ticket marked as complete",
        "transport_requests_created": transport_requests_created
    }

@router.delete("/itinerary/{itinerary_id}")
async def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete flight itinerary"""
    
    itinerary = db.query(FlightItinerary).filter(
        FlightItinerary.id == itinerary_id,
        FlightItinerary.user_email == current_user.email
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=404,
            detail="Itinerary not found"
        )
    
    # Check if trying to delete arrival itinerary when departure exists
    if itinerary.itinerary_type == "arrival":
        departure_exists = db.query(FlightItinerary).filter(
            FlightItinerary.event_id == itinerary.event_id,
            FlightItinerary.user_email == current_user.email,
            FlightItinerary.itinerary_type == "departure"
        ).first()
        
        if departure_exists:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete arrival itinerary when departure itinerary exists. Delete departure first."
            )
    
    db.delete(itinerary)
    db.commit()
    
    return {
        "status": "success",
        "message": "Itinerary deleted successfully"
    }

@router.get("/participant/{participant_id}")
async def get_participant_itineraries(
    participant_id: int,
    event_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get flight itineraries for a specific participant (admin endpoint)"""
    
    try:
        # Get participant details
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id
        ).first()
        
        if not participant:
            return []
        
        # Build query
        query = db.query(FlightItinerary).filter(
            FlightItinerary.user_email == participant.email
        )
        
        if event_id:
            query = query.filter(FlightItinerary.event_id == event_id)
        else:
            query = query.filter(FlightItinerary.event_id == participant.event_id)
        
        itineraries = query.all()
        
        result = []
        for it in itineraries:
            try:
                itinerary_data = {
                    "id": it.id,
                    "departure_city": it.departure_airport,
                    "arrival_city": it.arrival_airport,
                    "departure_date": it.departure_date.strftime("%Y-%m-%d") if it.departure_date else "",
                    "departure_time": it.departure_date.strftime("%H:%M") if it.departure_date else "",
                    "arrival_date": it.arrival_date.strftime("%Y-%m-%d") if it.arrival_date else "",
                    "arrival_time": it.arrival_date.strftime("%H:%M") if it.arrival_date else "",
                    "airline": it.airline or "",
                    "flight_number": it.flight_number or "",
                    "booking_reference": getattr(it, 'booking_reference', None),
                    "seat_number": getattr(it, 'seat_number', None),
                    "ticket_type": it.itinerary_type,
                    "status": "confirmed" if it.confirmed else "pending",
                    "created_at": it.created_at.isoformat() if hasattr(it, 'created_at') and it.created_at else ""
                }
                result.append(itinerary_data)
            except Exception:
                continue
        
        return result
        
    except Exception:
        return []