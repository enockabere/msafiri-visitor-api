from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.transport_request import TransportRequest
from app.models.flight_itinerary import FlightItinerary
from app.models.user import User
from app.core.deps import get_current_user
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter()

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

@router.get("/transport-requests/event/{event_id}")
def get_transport_requests_by_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    print(f"DEBUG API: Getting transport requests for event {event_id}")
    
    requests = db.query(TransportRequest).filter(
        TransportRequest.event_id == event_id
    ).all()
    
    print(f"DEBUG API: Found {len(requests)} transport requests")
    for req in requests:
        print(f"DEBUG API: Request {req.id}: {req.pickup_address} -> {req.dropoff_address}, Status: {req.status}, Notes: {req.notes}")
    
    return {"transport_requests": [
        {
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
            "created_at": req.created_at.isoformat() if req.created_at else None
        } for req in requests
    ]}

@router.post("/create-missing-transport-requests/{event_id}")
def create_missing_transport_requests(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create transport requests for confirmed itineraries that don't have them"""
    
    print(f"DEBUG API: Creating missing transport requests for event {event_id}, user {current_user.email}")
    
    # Get confirmed itineraries without transport requests
    confirmed_itineraries = db.query(FlightItinerary).filter(
        FlightItinerary.event_id == event_id,
        FlightItinerary.user_email == current_user.email,
        FlightItinerary.confirmed == True
    ).all()
    
    print(f"DEBUG API: Found {len(confirmed_itineraries)} confirmed itineraries")
    
    transport_requests_created = []
    
    for itinerary in confirmed_itineraries:
        # Check if transport request already exists
        existing_request = db.query(TransportRequest).filter(
            TransportRequest.flight_itinerary_id == itinerary.id,
            TransportRequest.user_email == current_user.email
        ).first()
        
        if existing_request:
            print(f"DEBUG API: Transport request already exists for itinerary {itinerary.id}")
            continue
            
        print(f"DEBUG API: Creating transport request for {itinerary.itinerary_type} itinerary {itinerary.id}")
        
        if itinerary.itinerary_type == "arrival":
            pickup_addr = itinerary.arrival_airport or itinerary.departure_airport
            dropoff_addr = itinerary.destination or "Event Location"
            pickup_time = itinerary.arrival_date or itinerary.departure_date
            notes = "Airport pickup for arrival flight"
            
        elif itinerary.itinerary_type == "departure":
            pickup_addr = itinerary.pickup_location or "Event Location"
            dropoff_addr = itinerary.departure_airport
            pickup_time = itinerary.departure_date - timedelta(hours=2)
            notes = "Airport drop-off for departure flight"
        else:
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
            status="created"
        )
        
        db.add(transport_request)
        transport_requests_created.append(itinerary.itinerary_type)
        print(f"DEBUG API: Added {itinerary.itinerary_type} transport request")
    
    try:
        db.commit()
        print(f"DEBUG API: Successfully created {len(transport_requests_created)} transport requests")
    except Exception as e:
        print(f"DEBUG API: Error creating transport requests: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "status": "success",
        "transport_requests_created": transport_requests_created,
        "message": f"Created {len(transport_requests_created)} transport requests"
    }