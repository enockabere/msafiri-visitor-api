from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.transport_request import TransportRequest
from app.models.flight_itinerary import FlightItinerary
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime

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
    requests = db.query(TransportRequest).filter(
        TransportRequest.event_id == event_id
    ).all()
    
    return {"transport_requests": [
        {
            "id": req.id,
            "pickup_address": req.pickup_address,
            "dropoff_address": req.dropoff_address,
            "pickup_time": req.pickup_time,
            "passenger_name": req.passenger_name,
            "passenger_phone": req.passenger_phone,
            "vehicle_type": req.vehicle_type,
            "flight_details": req.flight_details,
            "status": req.status,
            "created_at": req.created_at
        } for req in requests
    ]}