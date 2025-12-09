from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.flight_itinerary import FlightItinerary
from app.models.event_participant import EventParticipant
from datetime import datetime

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
        "departure_date": itinerary.departure_date.isoformat() if itinerary.departure_date else None,
        "departure_time": itinerary.departure_time if itinerary.departure_time else None,
        "arrival_date": itinerary.arrival_date.isoformat() if itinerary.arrival_date else None,
        "arrival_time": itinerary.arrival_time if itinerary.arrival_time else None,
        "airline": itinerary.airline,
        "flight_number": itinerary.flight_number,
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
            departure_city=flight_data.get("departure_airport"),  # Mobile sends departure_airport, DB has departure_city
            arrival_city=flight_data.get("arrival_airport"),  # Mobile sends arrival_airport, DB has arrival_city
            departure_date=departure_date,
            arrival_date=arrival_date,
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
    """Confirm flight itineraries"""
    print(f"DEBUG: Confirming itineraries: {itinerary_data}")

    itinerary_ids = itinerary_data.get("itinerary_ids", [])

    if not itinerary_ids:
        return {"message": "No itineraries to confirm"}

    # Update all specified itineraries to confirmed
    for itinerary_id in itinerary_ids:
        itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.id == itinerary_id,
            FlightItinerary.user_email == current_user.email
        ).first()

        if itinerary:
            itinerary.status = "confirmed"

    db.commit()

    return {"message": f"Confirmed {len(itinerary_ids)} itineraries successfully"}