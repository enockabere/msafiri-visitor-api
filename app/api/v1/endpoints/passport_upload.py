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
import json
import hashlib
import os

router = APIRouter()

def _slugify_record_id(record_id: int) -> str:
    """Create a secure slug from record ID to prevent enumeration attacks"""
    # Use a secret salt from environment or default
    salt = os.getenv('LOI_SALT', 'msf-loi-secure-salt-2024')
    
    # Create a hash using record_id + salt
    hash_input = f"{record_id}-{salt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    
    # Take first 12 characters and append record_id for uniqueness
    # This makes it hard to guess but still allows reverse lookup
    slugified = f"{hash_digest[:12]}-{record_id}"
    
    return slugified

def _extract_record_id_from_slug(slug: str) -> int:
    """Extract original record ID from slugified version"""
    try:
        # Split by last dash and get the record_id part
        parts = slug.split('-')
        if len(parts) >= 2:
            return int(parts[-1])
        else:
            raise ValueError("Invalid slug format")
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail="Invalid LOI reference format"
        )

class PassportUploadRequest(BaseModel):
    image_data: str  # base64 encoded image
    event_id: int

class PassportConfirmationRequest(BaseModel):
    record_id: int
    event_id: int
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
        
        # Get the record ID but don't save it yet - only save after confirmation
        record_id = result["result"]["record_id"]
        
        # Generate the public LOI URL with slugified record ID
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        slugified_id = _slugify_record_id(record_id)
        loi_url = f"{base_url}/public/loi/{slugified_id}"
        
        print(f"✅ PASSPORT UPLOAD SUCCESS: User={current_user.email}, Event={request.event_id}, RecordID={record_id}")
        
        return {
            "status": "success",
            "extracted_data": result["result"]["extracted_data"],
            "record_id": record_id,
            "loi_url": loi_url,
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
        
        # Generate the public LOI URL with slugified record ID
        import os
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        slugified_id = _slugify_record_id(request.record_id)
        loi_url = f"{base_url}/public/loi/{slugified_id}"
        
        print(f"🔗 PUBLIC LOI URL GENERATED: {loi_url}")
        print(f"🔗 BASE URL FROM ENV: {base_url}")
        print(f"🔗 RECORD ID: {request.record_id}")
        
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
            "confirmed": request.confirmed,
            "url": loi_url
        }
        
        print(f"🔗 URL IN PAYLOAD: {payload['url']}")
        
        print(f"📤 SENDING TO EXTERNAL API: {API_URL}")
        print(f"📤 HEADERS: {headers}")
        print(f"📤 PAYLOAD WITH PUBLIC URL: {json.dumps(payload, indent=2)}")
        print(f"📤 CONFIRMING URL BEING PATCHED: {payload['url']}")
        
        response = requests.patch(API_URL, json=payload, headers=headers, timeout=30)
        
        print(f"📥 EXTERNAL API RESPONSE:")
        print(f"📥 Status Code: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        print(f"📥 Response Text: {response.text}")
        
        if response.status_code not in [200, 204]:
            print(f"❌ EXTERNAL API ERROR: Status {response.status_code}")
            print(f"❌ Error Response: {response.text}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to confirm passport data: {response.text}"
            )
        
        # Use event_id from the request
        event_id = request.event_id
        
        # Now save the record ID only after successful confirmation
        existing_record = db.query(PassportRecord).filter(
            PassportRecord.user_email == current_user.email,
            PassportRecord.event_id == event_id
        ).first()
        
        if existing_record:
            # Update existing record
            existing_record.record_id = request.record_id
        else:
            # Create new record
            passport_record = PassportRecord(
                user_email=current_user.email,
                event_id=event_id,
                record_id=request.record_id
            )
            db.add(passport_record)
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
            print(f"✅ DATABASE UPDATE: passport_document set to True for participant {participant.id}")
        else:
            print(f"⚠️ PASSPORT CONFIRMATION WARNING: No participant found for email {current_user.email}, event_id {event_id}")
        
        # Final status check
        final_participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()
        
        final_status = final_participant.passport_document if final_participant else False
        print(f"🏁 PASSPORT PROCESS COMPLETE: User={current_user.email}, Event={event_id}, FinalStatus={final_status}")
        
        # Generate the public LOI URL for mobile app with slugified record ID
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        slugified_id = _slugify_record_id(request.record_id)
        loi_url = f"{base_url}/public/loi/{slugified_id}"
        
        print(f"📱 MOBILE APP LOI URL: {loi_url}")
        
        api_response = {
            "status": "success",
            "message": "Passport confirmed and checklist updated",
            "completion_status": final_status,
            "participant_updated": completion_status,
            "loi_url": loi_url,
            "record_id": request.record_id
        }
        
        print(f"🏁 FINAL API RESPONSE TO MOBILE:")
        print(f"🏁 {json.dumps(api_response, indent=2)}")
        print(f"🏁 LOI URL RETURNED TO MOBILE: {api_response['loi_url']}")
        print(f"🏁 RECORD ID: {api_response['record_id']}")
        print(f"🏁 FULL PUBLIC URL: http://41.90.97.253:8001/public/loi/{slugified_id}")
        print(f"🔒 SECURITY: Record ID {request.record_id} slugified to {slugified_id}")
        
        return api_response
        
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
        "slugified_id": _slugify_record_id(passport_record.record_id),
        "created_at": passport_record.created_at.isoformat() if passport_record.created_at else None
    }

@router.get("/loi/{slug}")
async def get_loi_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get LOI document by slugified record ID (public endpoint)"""
    
    try:
        # Extract the original record_id from the slug
        record_id = _extract_record_id_from_slug(slug)
        
        # Verify the slug is valid by re-generating it
        expected_slug = _slugify_record_id(record_id)
        if slug != expected_slug:
            raise HTTPException(
                status_code=404,
                detail="Invalid LOI reference"
            )
        
        # Forward to external API to get the actual LOI document
        import os
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/loi/{record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        headers = {
            "x-api-key": API_KEY
        }
        
        response = requests.get(API_URL, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="LOI document not found"
            )
        elif response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Error retrieving LOI document"
            )
        
        # Return the LOI document content
        return response.json()
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid LOI reference format"
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=500,
            detail="Error connecting to LOI service"
        )