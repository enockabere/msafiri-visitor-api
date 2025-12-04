from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Dict, Any
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.travel_checklist_progress import TravelChecklistProgress
from app.models.flight_itinerary import FlightItinerary
from pydantic import BaseModel
from datetime import datetime
from app.core.email_service import email_service
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db.database import Base

router = APIRouter()

class ChecklistProgressUpdate(BaseModel):
    checklist_items: Dict[str, bool]
    completed: bool

class PostponeItineraryRequest(BaseModel):
    reminder_date: str
    user_email: str

class FlightTicketData(BaseModel):
    event_id: int
    departure_airport: str
    arrival_airport: str = None
    departure_date: str = None
    arrival_date: str = None
    airline: str = None
    flight_number: str = None
    itinerary_type: str = "arrival"

class ItineraryReminder(Base):
    __tablename__ = "itinerary_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    reminder_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

@router.get("/progress/{event_id}")
async def get_checklist_progress(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get travel checklist progress for current user and event"""
    progress = db.query(TravelChecklistProgress).filter(
        TravelChecklistProgress.event_id == event_id,
        TravelChecklistProgress.user_email == current_user.email
    ).first()
    
    if not progress:
        return {"checklist_items": {}, "completed": False}
    
    return {
        "checklist_items": progress.checklist_items,
        "completed": progress.completed,
        "updated_at": progress.updated_at
    }

@router.post("/progress/{event_id}")
async def save_checklist_progress(
    event_id: int,
    progress_data: ChecklistProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save travel checklist progress for current user and event"""
    
    print(f"🔍 TRAVEL CHECKLIST DEBUG: Endpoint called for event {event_id}, user {current_user.email}")
    print(f"🔍 TRAVEL CHECKLIST DEBUG: Raw progress data: {progress_data}")
    
    # Server-side validation of completion status
    # Don't trust the client's completed flag - calculate it ourselves
    checklist_items = progress_data.checklist_items
    
    # Calculate actual completion based on all items being true
    server_calculated_completed = all(checklist_items.values()) if checklist_items else False
    
    print(f"🔍 API DEBUG: Saving checklist progress for event {event_id}, user {current_user.email}")
    print(f"🔍 API DEBUG: Client sent completed: {progress_data.completed}")
    print(f"🔍 API DEBUG: Server calculated completed: {server_calculated_completed}")
    print(f"🔍 API DEBUG: Checklist items: {checklist_items}")
    
    # Check if progress already exists
    existing_progress = db.query(TravelChecklistProgress).filter(
        TravelChecklistProgress.event_id == event_id,
        TravelChecklistProgress.user_email == current_user.email
    ).first()
    
    if existing_progress:
        # Update existing progress with server-calculated completion
        existing_progress.checklist_items = checklist_items
        existing_progress.completed = server_calculated_completed
        print(f"🔍 API DEBUG: Updated existing progress - completed: {server_calculated_completed}")
    else:
        # Create new progress record with server-calculated completion
        new_progress = TravelChecklistProgress(
            event_id=event_id,
            user_email=current_user.email,
            checklist_items=checklist_items,
            completed=server_calculated_completed
        )
        db.add(new_progress)
        print(f"🔍 API DEBUG: Created new progress - completed: {server_calculated_completed}")
    
    db.commit()
    return {
        "message": "Progress saved successfully",
        "completed": server_calculated_completed,
        "items_count": len(checklist_items),
        "completed_count": sum(1 for v in checklist_items.values() if v)
    }

@router.get("/progress/{event_id}/{participant_email}")
async def get_participant_checklist_progress(
    event_id: int,
    participant_email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get travel checklist progress for a specific participant (admin only)"""
    

    
    # Check if current user has admin permissions for this event
    # For now, allow any authenticated user to view progress
    
    progress = db.query(TravelChecklistProgress).filter(
        TravelChecklistProgress.event_id == event_id,
        TravelChecklistProgress.user_email == participant_email
    ).first()
    
    if not progress:
        return {"checklist_items": {}, "completed": False}
    
    return {
        "checklist_items": progress.checklist_items,
        "completed": progress.completed,
        "updated_at": progress.updated_at
    }

@router.post("/postpone-itinerary/{event_id}")
async def postpone_itinerary(
    event_id: int,
    request: PostponeItineraryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Postpone flight itinerary creation with reminder"""
    
    try:
        reminder_date = datetime.fromisoformat(request.reminder_date.replace('Z', '+00:00'))
        
        # Delete any existing active reminders for this user/event (only one allowed)
        existing_reminders = db.query(ItineraryReminder).filter(
            ItineraryReminder.event_id == event_id,
            ItineraryReminder.user_email == request.user_email,
            ItineraryReminder.is_active == True
        ).all()
        
        for existing in existing_reminders:
            existing.is_active = False
        
        # Store new reminder in database
        reminder = ItineraryReminder(
            event_id=event_id,
            user_email=request.user_email,
            reminder_date=reminder_date
        )
        db.add(reminder)
        db.commit()
        
        # Send confirmation email
        email_service.send_notification_email(
            to_email=request.user_email,
            user_name=current_user.full_name or current_user.email,
            title="Flight Itinerary Reminder Set",
            message=f"Your flight itinerary reminder has been set for {reminder_date.strftime('%B %d, %Y')}. You will receive a notification on this date to complete your flight itinerary for the event."
        )
        
        return {"message": "Itinerary reminder set successfully", "reminder_id": reminder.id}
        
    except Exception as e:
        pass
        raise HTTPException(status_code=500, detail="Failed to set reminder")

@router.get("/reminders/{event_id}")
async def get_reminders(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active reminders for current user and event"""
    
    reminders = db.query(ItineraryReminder).filter(
        ItineraryReminder.event_id == event_id,
        ItineraryReminder.user_email == current_user.email,
        ItineraryReminder.is_active == True
    ).all()
    
    return {
        "reminders": [
            {
                "id": r.id,
                "reminder_date": r.reminder_date.isoformat(),
                "created_at": r.created_at.isoformat()
            } for r in reminders
        ]
    }

@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a reminder"""
    
    reminder = db.query(ItineraryReminder).filter(
        ItineraryReminder.id == reminder_id,
        ItineraryReminder.user_email == current_user.email
    ).first()
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    reminder.is_active = False
    db.commit()
    
    return {"message": "Reminder deleted successfully"}

@router.post("/flight-ticket/{event_id}")
async def save_flight_ticket(
    event_id: int,
    ticket_data: FlightTicketData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save flight ticket data from mobile app"""
    
    print(f"🛩️ FLIGHT TICKET DEBUG: Endpoint called for event {event_id}, user {current_user.email}")
    print(f"🛩️ FLIGHT TICKET DEBUG: Ticket data received: {ticket_data.dict()}")
    
    try:
        # Parse datetime strings
        departure_date = None
        arrival_date = None
        
        if ticket_data.departure_date:
            departure_date = datetime.fromisoformat(ticket_data.departure_date.replace('Z', '+00:00'))
            print(f"🛩️ FLIGHT TICKET DEBUG: Parsed departure_date: {departure_date}")
        
        if ticket_data.arrival_date:
            arrival_date = datetime.fromisoformat(ticket_data.arrival_date.replace('Z', '+00:00'))
            print(f"🛩️ FLIGHT TICKET DEBUG: Parsed arrival_date: {arrival_date}")
        
        # Check if flight itinerary already exists for this user/event
        existing_itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.user_email == current_user.email,
            FlightItinerary.event_id == event_id
        ).first()
        
        if existing_itinerary:
            # Update existing itinerary
            existing_itinerary.airline = ticket_data.airline
            existing_itinerary.flight_number = ticket_data.flight_number
            existing_itinerary.departure_airport = ticket_data.departure_airport
            existing_itinerary.arrival_airport = ticket_data.arrival_airport
            existing_itinerary.departure_date = departure_date
            existing_itinerary.arrival_date = arrival_date
            existing_itinerary.itinerary_type = ticket_data.itinerary_type
            print(f"🛩️ FLIGHT TICKET DEBUG: Updated existing itinerary ID: {existing_itinerary.id}")
        else:
            # Create new flight itinerary
            itinerary = FlightItinerary(
                event_id=event_id,
                user_email=current_user.email,
                airline=ticket_data.airline,
                flight_number=ticket_data.flight_number,
                departure_airport=ticket_data.departure_airport,
                arrival_airport=ticket_data.arrival_airport,
                departure_date=departure_date,
                arrival_date=arrival_date,
                itinerary_type=ticket_data.itinerary_type,
                confirmed=True
            )
            
            db.add(itinerary)
            print(f"🛩️ FLIGHT TICKET DEBUG: Created new itinerary")
        
        db.commit()
        print(f"🛩️ FLIGHT TICKET DEBUG: Successfully saved flight ticket data")
        
        return {"message": "Flight ticket saved successfully", "status": "success"}
        
    except Exception as e:
        print(f"🛩️ FLIGHT TICKET DEBUG: Error saving flight ticket: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save flight ticket: {str(e)}")

@router.post("/save-ticket-data/{event_id}")
async def save_ticket_data_alternative(
    event_id: int,
    ticket_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alternative endpoint for saving ticket data (in case mobile app uses different endpoint)"""
    
    print(f"🎟️ TICKET DATA DEBUG: Alternative endpoint called for event {event_id}, user {current_user.email}")
    print(f"🎟️ TICKET DATA DEBUG: Raw ticket data: {ticket_data}")
    
    try:
        # Parse datetime strings if they exist
        departure_date = None
        arrival_date = None
        
        if ticket_data.get("departure_date"):
            departure_date = datetime.fromisoformat(ticket_data["departure_date"].replace('Z', '+00:00'))
        
        if ticket_data.get("arrival_date"):
            arrival_date = datetime.fromisoformat(ticket_data["arrival_date"].replace('Z', '+00:00'))
        
        # Create or update flight itinerary
        existing_itinerary = db.query(FlightItinerary).filter(
            FlightItinerary.user_email == current_user.email,
            FlightItinerary.event_id == event_id
        ).first()
        
        if existing_itinerary:
            # Update existing
            existing_itinerary.airline = ticket_data.get("airline")
            existing_itinerary.flight_number = ticket_data.get("flight_number")
            existing_itinerary.departure_airport = ticket_data.get("departure_airport", ticket_data.get("from"))
            existing_itinerary.arrival_airport = ticket_data.get("arrival_airport", ticket_data.get("to"))
            existing_itinerary.departure_date = departure_date
            existing_itinerary.arrival_date = arrival_date
            print(f"🎟️ TICKET DATA DEBUG: Updated existing itinerary")
        else:
            # Create new
            itinerary = FlightItinerary(
                event_id=event_id,
                user_email=current_user.email,
                airline=ticket_data.get("airline"),
                flight_number=ticket_data.get("flight_number"),
                departure_airport=ticket_data.get("departure_airport", ticket_data.get("from")),
                arrival_airport=ticket_data.get("arrival_airport", ticket_data.get("to")),
                departure_date=departure_date,
                arrival_date=arrival_date,
                itinerary_type=ticket_data.get("itinerary_type", "arrival"),
                confirmed=True
            )
            db.add(itinerary)
            print(f"🎟️ TICKET DATA DEBUG: Created new itinerary")
        
        db.commit()
        print(f"🎟️ TICKET DATA DEBUG: Successfully saved ticket data")
        
        return {"message": "Ticket data saved successfully", "status": "success"}
        
    except Exception as e:
        print(f"🎟️ TICKET DATA DEBUG: Error: {str(e)}")
        db.rollback()
        return {"message": f"Error saving ticket data: {str(e)}", "status": "error"}