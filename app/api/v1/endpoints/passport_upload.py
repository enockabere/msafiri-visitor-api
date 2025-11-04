from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.passport_record import PassportRecord
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
    date_of_issue: str
    gender: str
    nationality: str
    user_email: str
    location_id: Dict[str, Any]
    confirmed: bool = True

@router.post("/upload-passport")
async def upload_passport(
    request: PassportUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload passport image for processing"""
    
    print(f"🚀 PASSPORT UPLOAD START: User={current_user.email}, Event={request.event_id}")
    
    # Validate image format
    try:
        image_data = base64.b64decode(request.image_data)
        # Check for common image file signatures
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
    
    # Call external passport processing API
    try:
        import os
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/extract-passport-data"
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
                detail="Failed to process passport image"
            )
        
        result = response.json()
        
        if result.get("result", {}).get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail="Passport processing failed"
            )
        
        # Save the record ID for future reference
        record_id = result["result"]["record_id"]
        
        # Check if record already exists
        existing_record = db.query(PassportRecord).filter(
            PassportRecord.user_email == current_user.email,
            PassportRecord.event_id == request.event_id
        ).first()
        
        if existing_record:
            # Update existing record
            existing_record.record_id = record_id
        else:
            # Create new record
            passport_record = PassportRecord(
                user_email=current_user.email,
                event_id=request.event_id,
                record_id=record_id
            )
            db.add(passport_record)
        
        db.commit()
        
        print(f"✅ PASSPORT UPLOAD SUCCESS: User={current_user.email}, Event={request.event_id}, RecordID={record_id}")
        
        return {
            "status": "success",
            "extracted_data": result["result"]["extracted_data"],
            "record_id": record_id,
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
    
    print(f"📋 PASSPORT CONFIRM START: User={current_user.email}, RecordID={request.record_id}")
    
    # Validate all required fields are not empty
    required_fields = {
        'passport_no': request.passport_no,
        'given_names': request.given_names,
        'surname': request.surname,
        'issue_country': request.issue_country,
        'date_of_birth': request.date_of_birth,
        'date_of_expiry': request.date_of_expiry,
        'date_of_issue': request.date_of_issue,
        'gender': request.gender,
        'nationality': request.nationality
    }
    
    # Check for empty or placeholder values
    invalid_date_patterns = ['', 'YYYY-MM-DD', 'yyyy-mm-dd', 'DD/MM/YYYY', 'MM/DD/YYYY']
    
    empty_fields = []
    for field, value in required_fields.items():
        if not value or not value.strip():
            empty_fields.append(field)
        elif field.startswith('date_') and value.strip() in invalid_date_patterns:
            empty_fields.append(f"{field} (invalid date format)")
    
    if empty_fields:
        raise HTTPException(
            status_code=400,
            detail=f"The following fields are required and cannot be empty: {', '.join(empty_fields)}"
        )
    
    # Additional validation for date_of_issue specifically
    if not request.date_of_issue or request.date_of_issue.strip() in invalid_date_patterns:
        raise HTTPException(
            status_code=400,
            detail="Date of Issue is required and must be a valid date"
        )
    
    print(f"📋 VALIDATION: All fields validated successfully")
    print(f"📋 Date of Issue: '{request.date_of_issue}'")
    print(f"📋 Passport No: '{request.passport_no}'")
    print(f"📋 Given Names: '{request.given_names}'")
    print(f"📋 Surname: '{request.surname}'")
    
    try:
        # Update passport data on external API
        import os
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/update-passport-data/{request.record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
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
            "date_of_issue": request.date_of_issue,
            "gender": request.gender,
            "nationality": request.nationality,
            "user_email": request.user_email,
            "location_id": request.location_id,
            "confirmed": request.confirmed
        }
        
        response = requests.patch(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=400,
                detail="Failed to confirm passport data"
            )
        
        # Find the event ID from the passport record
        passport_record = db.query(PassportRecord).filter(
            PassportRecord.record_id == request.record_id,
            PassportRecord.user_email == current_user.email
        ).first()
        
        print(f"📋 PASSPORT CONFIRMATION: Looking for passport record with record_id: {request.record_id}")
        print(f"📋 PASSPORT CONFIRMATION: Found passport record: {passport_record is not None}")
        
        if not passport_record:
            print(f"📋 PASSPORT CONFIRMATION: WARNING - No passport record found for record_id {request.record_id}")
            # Still return success since external API was updated successfully
            return {
                "status": "success",
                "message": "Passport confirmed on external API, but local record not found"
            }
        
        event_id = passport_record.event_id
        print(f"📋 PASSPORT CONFIRMATION: Found event_id: {event_id}")
        
        # Update participant passport status for the specific event - no sensitive data stored
        participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()
        
        print(f"📋 PASSPORT CONFIRMATION: Looking for participant with email: {current_user.email}, event_id: {event_id}")
        print(f"📋 PASSPORT CONFIRMATION: Found participant: {participant is not None}")
        
        completion_status = False
        if participant:
            print(f"📋 PASSPORT CONFIRMATION: Updating participant {participant.id} passport status to True")
            participant.passport_document = True
            db.commit()
            db.refresh(participant)
            completion_status = True
            print(f"✅ PASSPORT CONFIRMATION SUCCESS: Participant {participant.id} passport_document=True")
        else:
            print(f"⚠️ PASSPORT CONFIRMATION WARNING: No participant found for email {current_user.email}, event_id {event_id}")
        
        # Final status check
        final_participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()
        
        final_status = final_participant.passport_document if final_participant else False
        print(f"🏁 PASSPORT PROCESS COMPLETE: User={current_user.email}, Event={event_id}, FinalStatus={final_status}")
        
        return {
            "status": "success",
            "message": "Passport confirmed and checklist updated",
            "completion_status": final_status,
            "participant_updated": completion_status
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
        EventParticipant.email == current_user.email
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

@router.get("/events/{event_id}/passport-record")
async def get_passport_record(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get passport record ID for user and event"""
    
    passport_record = db.query(PassportRecord).filter(
        PassportRecord.user_email == current_user.email,
        PassportRecord.event_id == event_id
    ).first()
    
    if not passport_record:
        raise HTTPException(
            status_code=404,
            detail="No passport record found for this user and event"
        )
    
    return {
        "record_id": passport_record.record_id,
        "created_at": passport_record.created_at.isoformat() if passport_record.created_at else None
    }