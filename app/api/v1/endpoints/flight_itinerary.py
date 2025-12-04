from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.api import deps
from app.db.database import get_db

router = APIRouter()

@router.get("/participant/{participant_id}")
def get_participant_flight_itinerary(
    participant_id: int,
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get flight itinerary for a participant"""
    # For now, return empty array since flight itinerary feature might not be implemented
    return []