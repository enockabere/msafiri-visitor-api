from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Dict, Any
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.travel_checklist_progress import TravelChecklistProgress
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