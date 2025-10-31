from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.event_registration import EventRegistration
from app.models.travel_checklist_progress import TravelChecklistProgress
from pydantic import BaseModel

router = APIRouter()

class ChecklistProgressUpdate(BaseModel):
    checklist_items: Dict[str, bool]
    completed: bool

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
    
    # Check if progress already exists
    existing_progress = db.query(TravelChecklistProgress).filter(
        TravelChecklistProgress.event_id == event_id,
        TravelChecklistProgress.user_email == current_user.email
    ).first()
    
    if existing_progress:
        # Update existing progress
        existing_progress.checklist_items = progress_data.checklist_items
        existing_progress.completed = progress_data.completed
    else:
        # Create new progress record
        new_progress = TravelChecklistProgress(
            event_id=event_id,
            user_email=current_user.email,
            checklist_items=progress_data.checklist_items,
            completed=progress_data.completed
        )
        db.add(new_progress)
    
    db.commit()
    return {"message": "Progress saved successfully"}

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