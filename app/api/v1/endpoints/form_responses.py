from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.form_field import FormResponse
from app.api import deps
from typing import List

router = APIRouter()

@router.get("/participant/{participant_id}")
async def get_participant_form_responses(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_user)
):
    """Get all form responses for a specific participant"""
    
    responses = db.query(FormResponse).filter(
        FormResponse.registration_id == participant_id
    ).all()
    
    return [
        {
            "id": response.id,
            "field_id": response.field_id,
            "field_value": response.field_value,
            "created_at": response.created_at
        }
        for response in responses
    ]