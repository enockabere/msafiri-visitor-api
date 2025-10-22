# File: app/api/v1/endpoints/event_status.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, date
from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.event import Event
from app.models.user import User

router = APIRouter()

class EventStatusUpdate(BaseModel):
    status: str

@router.put("/{event_id}/status", operation_id="update_event_status_unique")
def update_event_status(
    event_id: int,
    status_data: EventStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update event status with validation"""
    
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Validate status transitions
    valid_statuses = ["Draft", "Published", "Ongoing", "Completed", "Cancelled"]
    if status_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    current_date = date.today()
    
    # Handle both string and date types
    if isinstance(event.start_date, str):
        start_date = datetime.strptime(event.start_date, "%Y-%m-%d").date()
    else:
        start_date = event.start_date
        
    if isinstance(event.end_date, str):
        end_date = datetime.strptime(event.end_date, "%Y-%m-%d").date()
    else:
        end_date = event.end_date
    
    # Status validation rules
    if status_data.status == "Published":
        if event.status != "Draft":
            raise HTTPException(status_code=400, detail="Can only publish draft events")
    
    elif status_data.status == "Cancelled":
        if current_date >= start_date:
            raise HTTPException(status_code=400, detail="Cannot cancel event that has already started")
        if event.status in ["Completed", "Ongoing"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or ongoing events")
    
    elif status_data.status == "Ongoing":
        if current_date < start_date:
            raise HTTPException(status_code=400, detail="Event has not started yet")
        if current_date > end_date:
            raise HTTPException(status_code=400, detail="Event has already ended")
    
    elif status_data.status == "Completed":
        if current_date <= end_date:
            raise HTTPException(status_code=400, detail="Event has not ended yet")
    
    # Update status
    event.status = status_data.status
    db.commit()
    db.refresh(event)
    
    return {"message": f"Event status updated to {status_data.status}", "event": event}

@router.get("/{event_id}/status/suggestions", operation_id="get_status_suggestions_unique")
def get_status_suggestions(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get suggested status based on event dates"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    current_date = date.today()
    
    # Handle both string and date types
    if isinstance(event.start_date, str):
        start_date = datetime.strptime(event.start_date, "%Y-%m-%d").date()
    else:
        start_date = event.start_date
        
    if isinstance(event.end_date, str):
        end_date = datetime.strptime(event.end_date, "%Y-%m-%d").date()
    else:
        end_date = event.end_date
    
    suggestions = []
    
    if event.status == "Draft":
        suggestions.append({"status": "Published", "reason": "Ready to publish"})
        if current_date < start_date:
            suggestions.append({"status": "Cancelled", "reason": "Cancel before start date"})
    
    elif event.status == "Published":
        if current_date >= start_date and current_date <= end_date:
            suggestions.append({"status": "Ongoing", "reason": "Event is currently happening"})
        elif current_date > end_date:
            suggestions.append({"status": "Completed", "reason": "Event has ended"})
        elif current_date < start_date:
            suggestions.append({"status": "Cancelled", "reason": "Cancel before start date"})
    
    elif event.status == "Ongoing":
        if current_date > end_date:
            suggestions.append({"status": "Completed", "reason": "Event has ended"})
    
    return {
        "current_status": event.status,
        "suggestions": suggestions,
        "event_dates": {
            "start_date": event.start_date,
            "end_date": event.end_date,
            "current_date": current_date.isoformat()
        }
    }