from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant
import requests
import base64
from typing import Dict, Any
from pydantic import BaseModel

router = APIRouter()

class PassportUploadRequest(BaseModel):
    image_data: str  # base64 encoded image
    event_id: int

class PassportConfirmationRequest(BaseModel):
    record_id: int
    passport_no: str
    given_names: str
    surname: str
    issue_country: str
    date_of_birth: str
    date_of_expiry: str
    gender: str
    nationality: str
    confirmed: bool = True

@router.post("/upload-passport")
async def upload_passport(
    request: PassportUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload passport image for processing"""
    
    # Verify user is registered for the event
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == request.event_id,
        EventParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="User not registered for this event"
        )
    
    # Call external passport processing API
    try:
        API_URL = "https://ko-hr.kenya.msf.org/api/v1/extract-passport-data"
        API_KEY = "n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW"
        
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
                detail="Failed to process passport image"
            )
        
        result = response.json()
        
        if result.get("result", {}).get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail="Passport processing failed"
            )
        
        return {
            "status": "success",
            "extracted_data": result["result"]["extracted_data"],
            "record_id": result["result"]["record_id"],
            "message": "Passport data extracted successfully"
        }
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.post("/confirm-passport")
async def confirm_passport(
    request: PassportConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm passport data and update checklist"""
    
    try:
        # Update passport data on external API
        API_URL = f"https://ko-hr.kenya.msf.org/api/v1/update-passport-data/{request.record_id}"
        API_KEY = "n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        }
        
        payload = {
            "passport_no": request.passport_no,
            "given_names": request.given_names,
            "surname": request.surname,
            "issue_country": request.issue_country,
            "date_of_birth": request.date_of_birth,
            "date_of_expiry": request.date_of_expiry,
            "gender": request.gender,
            "nationality": request.nationality,
            "confirmed": request.confirmed
        }
        
        response = requests.patch(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=400,
                detail="Failed to confirm passport data"
            )
        
        # Update participant passport status in our database
        participant = db.query(EventParticipant).filter(
            EventParticipant.user_id == current_user.id
        ).first()
        
        if participant:
            participant.passport_document = True
            db.commit()
        
        return {
            "status": "success",
            "message": "Passport confirmed and checklist updated"
        }
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"External API error: {str(e)}"
        )

@router.get("/events/{event_id}/checklist-status")
async def get_checklist_status(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get travel checklist completion status"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="User not registered for this event"
        )
    
    # Check if travelling internationally
    travelling_internationally = participant.travelling_internationally == "Yes"
    
    if not travelling_internationally:
        return {
            "travelling_internationally": False,
            "checklist_complete": True,
            "required_items": []
        }
    
    # Get travel requirements and check completion
    required_items = []
    completed_items = []
    
    if participant.passport_document:
        completed_items.append("passport")
    else:
        required_items.append("passport")
    
    if participant.ticket_document:
        completed_items.append("ticket")
    else:
        required_items.append("ticket")
    
    # Add other requirements based on travel requirements
    # This would be expanded based on the country travel requirements
    
    checklist_complete = len(required_items) == 0
    
    return {
        "travelling_internationally": True,
        "checklist_complete": checklist_complete,
        "required_items": required_items,
        "completed_items": completed_items
    }