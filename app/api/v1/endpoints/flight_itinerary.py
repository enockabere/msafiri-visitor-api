from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.flight_itinerary import FlightItinerary
from app.models.event import Event
import requests
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class TicketUploadRequest(BaseModel):
    image_data: str  # base64 encoded image
    event_id: int

class ItineraryRequest(BaseModel):
    event_id: int
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    departure_airport: str
    arrival_airport: str
    departure_date: str  # ISO format
    arrival_date: str    # ISO format
    itinerary_type: str  # 'arrival', 'departure', 'custom'

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
    
    # Create itinerary
    itinerary = FlightItinerary(
        event_id=request.event_id,
        user_email=current_user.email,
        airline=request.airline,
        flight_number=request.flight_number,
        departure_airport=request.departure_airport,
        arrival_airport=request.arrival_airport,
        departure_date=datetime.fromisoformat(request.departure_date),
        arrival_date=datetime.fromisoformat(request.arrival_date),
        itinerary_type=request.itinerary_type
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
                "arrival_date": it.arrival_date.isoformat(),
                "itinerary_type": it.itinerary_type,
                "confirmed": it.confirmed,
                "ticket_record_id": it.ticket_record_id
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
    
    # Update fields
    itinerary.airline = request.airline
    itinerary.flight_number = request.flight_number
    itinerary.departure_airport = request.departure_airport
    itinerary.arrival_airport = request.arrival_airport
    itinerary.departure_date = datetime.fromisoformat(request.departure_date)
    itinerary.arrival_date = datetime.fromisoformat(request.arrival_date)
    itinerary.itinerary_type = request.itinerary_type
    
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
    
    # Update itineraries as confirmed
    for itinerary_id in request.itinerary_ids:
        itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == itinerary_id,
            FlightItinerary.user_email == current_user.email
        ).first()
        
        if itinerary:
            itinerary.confirmed = True
    
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
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Itineraries confirmed and ticket marked as complete"
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
    
    db.delete(itinerary)
    db.commit()
    
    return {
        "status": "success",
        "message": "Itinerary deleted successfully"
    }