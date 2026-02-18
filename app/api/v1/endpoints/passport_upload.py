from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.passport_record import PassportRecord
from app.services.passport_extraction_service import passport_extraction_service
import base64
from typing import Dict, Any
from pydantic import BaseModel
import json
import hashlib
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Azure Blob Storage for passport images
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_PASSPORTS_CONTAINER = os.getenv("AZURE_PASSPORTS_CONTAINER", "passports")

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

async def upload_passport_to_azure(image_bytes: bytes, user_id: int, content_type: str = "image/jpeg") -> str:
    """Upload passport image to Azure Blob Storage and return URL."""
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage is not configured"
            )

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        container_client = blob_service_client.get_container_client(AZURE_PASSPORTS_CONTAINER)

        # Create container if it doesn't exist
        try:
            container_client.create_container(public_access='blob')
        except Exception:
            pass  # Container already exists

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
        unique_filename = f"passport_{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"

        blob_client = container_client.get_blob_client(unique_filename)
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            image_bytes,
            overwrite=True,
            content_settings=content_settings
        )

        return blob_client.url

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage SDK not installed"
        )
    except Exception as e:
        logger.error(f"Azure blob upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload passport image: {str(e)}"
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
    """Upload passport image for processing using Azure Document Intelligence"""

    logger.info(f"🚀 PASSPORT UPLOAD START: User={current_user.email}, Event={request.event_id}")

    # Validate image format
    try:
        image_data = base64.b64decode(request.image_data)
        # Check for common image file signatures and determine content type
        content_type = "image/jpeg"
        if image_data.startswith(b'\xff\xd8\xff'):  # JPEG
            content_type = "image/jpeg"
        elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
            content_type = "image/png"
        elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):  # GIF
            content_type = "image/gif"
        else:
            raise HTTPException(
                status_code=400,
                detail="Only image files (JPEG, PNG, GIF) are supported"
            )
    except HTTPException:
        raise
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

    try:
        # Upload passport image to Azure Blob Storage
        file_url = await upload_passport_to_azure(image_data, current_user.id, content_type)
        logger.info(f"📤 Passport image uploaded to Azure: {file_url}")

        # Extract passport data using Azure Document Intelligence
        extracted_data = await passport_extraction_service.extract_passport_data_from_bytes(image_data)
        logger.info(f"📋 Passport data extracted: {extracted_data.get('passport_number', 'N/A')}")

        # Transform extracted data to match the expected format for event checklist
        # The event checklist expects different field names
        # Calculate OCR score as percentage for mobile app
        ocr_quality_score = extracted_data.get("ocr_quality_score") or 0.0
        # Convert to percentage (0-100) or star rating (1-5) format
        score_percentage = round(ocr_quality_score * 100, 1) if ocr_quality_score else None

        checklist_extracted_data = {
            "passport_no": extracted_data.get("passport_number"),
            "given_names": extracted_data.get("given_names"),
            "surname": extracted_data.get("surname"),
            "date_of_birth": extracted_data.get("date_of_birth"),
            "date_of_expiry": extracted_data.get("expiry_date"),
            "date_of_issue": extracted_data.get("date_of_issue"),
            "gender": extracted_data.get("gender"),
            "nationality": extracted_data.get("nationality"),
            "issue_country": extracted_data.get("issue_country"),
            "full_name": extracted_data.get("full_name"),
            "ocr_quality_score": ocr_quality_score,
            "score": score_percentage,  # For mobile app compatibility
            "confidence_scores": extracted_data.get("confidence_scores", {}),
            "file_url": file_url
        }

        # Create a temporary record ID (will be replaced with actual DB record on confirmation)
        # Using participant ID + timestamp as a pseudo record ID
        temp_record_id = int(f"{participant.id}{int(datetime.utcnow().timestamp() % 100000)}")

        # For upload, generate a placeholder LOI URL
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        loi_url = f"{base_url}/public/loi/pending-{temp_record_id}"

        logger.info(f"✅ PASSPORT UPLOAD SUCCESS: User={current_user.email}, Event={request.event_id}")

        return {
            "status": "success",
            "extracted_data": checklist_extracted_data,
            "record_id": temp_record_id,
            "file_url": file_url,
            "loi_url": loi_url,
            "message": "Passport data extracted successfully using Document Intelligence"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Passport processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process passport: {str(e)}"
        )

@router.post("/confirm-passport")
async def confirm_passport(
    request: PassportConfirmationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm passport data and update checklist - stores data locally using Document Intelligence"""

    logger.info(f"📋 PASSPORT CONFIRM START: User={current_user.email}, RecordID={request.record_id}")

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

    logger.info(f"📋 VALIDATION: All fields validated successfully")

    try:
        event_id = request.event_id

        # Check for existing passport record for this user and event
        existing_record = db.query(PassportRecord).filter(
            PassportRecord.user_email == current_user.email,
            PassportRecord.event_id == event_id
        ).first()

        if existing_record:
            # Update existing record with passport data
            existing_record.record_id = request.record_id
            existing_record.passport_number = request.passport_no
            existing_record.given_names = request.given_names
            existing_record.surname = request.surname
            existing_record.date_of_birth = request.date_of_birth
            existing_record.date_of_expiry = request.date_of_expiry
            existing_record.date_of_issue = request.date_of_issue
            existing_record.gender = request.gender
            existing_record.nationality = request.nationality
            existing_record.issue_country = request.issue_country
            # Generate slug if it doesn't exist
            if not existing_record.slug:
                existing_record.generate_slug()
            db.commit()
            db.refresh(existing_record)
            passport_record = existing_record
        else:
            # Create new passport record with all data
            passport_record = PassportRecord(
                user_email=current_user.email,
                event_id=event_id,
                record_id=request.record_id,
                passport_number=request.passport_no,
                given_names=request.given_names,
                surname=request.surname,
                date_of_birth=request.date_of_birth,
                date_of_expiry=request.date_of_expiry,
                date_of_issue=request.date_of_issue,
                gender=request.gender,
                nationality=request.nationality,
                issue_country=request.issue_country
            )
            # Generate slug for new record
            passport_record.generate_slug()
            db.add(passport_record)
            db.commit()
            db.refresh(passport_record)

        actual_slug = passport_record.slug
        logger.info(f"📋 PASSPORT CONFIRMATION: Saved passport record with slug: {actual_slug}")

        # Update participant passport status for the specific event
        participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()

        completion_status = False
        if participant:
            logger.info(f"📋 PASSPORT CONFIRMATION: Updating participant {participant.id} passport status to True")
            participant.passport_document = True
            db.commit()
            db.refresh(participant)
            completion_status = True
            logger.info(f"✅ PASSPORT CONFIRMATION SUCCESS: Participant {participant.id} passport_document=True")
        else:
            logger.warning(f"⚠️ PASSPORT CONFIRMATION WARNING: No participant found for email {current_user.email}, event_id {event_id}")

        # Final status check
        final_participant = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == event_id
        ).first()

        final_status = final_participant.passport_document if final_participant else False
        logger.info(f"🏁 PASSPORT PROCESS COMPLETE: User={current_user.email}, Event={event_id}, FinalStatus={final_status}")

        # Generate the public LOI URL for mobile app using actual database slug
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        loi_url = f"{base_url}/public/loi/{actual_slug}"

        logger.info(f"📱 MOBILE APP LOI URL: {loi_url}")

        api_response = {
            "status": "success",
            "message": "Passport confirmed and checklist updated",
            "completion_status": final_status,
            "participant_updated": completion_status,
            "loi_url": loi_url,
            "record_id": request.record_id
        }

        logger.info(f"🏁 FINAL API RESPONSE: {json.dumps(api_response, indent=2)}")

        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Passport confirmation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to confirm passport data: {str(e)}"
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
        "slugified_id": passport_record.slug,
        "created_at": passport_record.created_at.isoformat() if passport_record.created_at else None
    }

@router.get("/loi/record/{record_id}")
async def redirect_to_loi_by_record_id(
    record_id: int,
    db: Session = Depends(get_db)
):
    """Redirect from raw record ID to slugified LOI URL"""
    from fastapi.responses import RedirectResponse
    import os
    
    try:
        # Generate slugified ID
        slugified_id = _slugify_record_id(record_id)
        
        # Get base URL for redirect
        base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        redirect_url = f"{base_url}/public/loi/{slugified_id}"
        
        print(f"🔄 LOI REDIRECT: Raw ID {record_id} -> Slugified {slugified_id}")
        print(f"🔄 REDIRECT URL: {redirect_url}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        print(f"❌ LOI REDIRECT ERROR: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid record ID: {record_id}"
        )

@router.get("/loi/{slug}")
async def get_loi_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get LOI document by slugified record ID (public endpoint)"""
    
    print(f"🔍 LOI FETCH START: Slug={slug}")
    
    try:
        # First try to find the passport record by slug in database
        passport_record = db.query(PassportRecord).filter(
            PassportRecord.slug == slug
        ).first()
        
        if not passport_record:
            print(f"❌ PASSPORT RECORD NOT FOUND: No record with slug '{slug}'")
            raise HTTPException(
                status_code=404,
                detail="Invalid LOI reference"
            )
        
        record_id = passport_record.record_id
        print(f"🔍 FOUND RECORD ID: {record_id} for slug: {slug}")
        
        # Get passport data from external API using the record_id
        import os
        API_URL = f"{os.getenv('PASSPORT_API_URL', 'https://ko-hr.kenya.msf.org/api/v1')}/get-passport-data/{record_id}"
        API_KEY = os.getenv('PASSPORT_API_KEY', 'n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW')
        
        print(f"🔍 CALLING EXTERNAL API: {API_URL}")
        
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Use the same format as the working Python script
        payload = {"passport_id": record_id}
        
        print(f"🔍 REQUEST HEADERS: {headers}")
        print(f"🔍 REQUEST PAYLOAD: {payload}")
        
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        print(f"🔍 EXTERNAL API RESPONSE:")
        print(f"🔍 Status Code: {response.status_code}")
        print(f"🔍 Response Headers: {dict(response.headers)}")
        print(f"🔍 Response Text: {response.text[:500]}..." if len(response.text) > 500 else response.text)
        
        if response.status_code == 404:
            print(f"❌ LOI DOCUMENT NOT FOUND: Record ID {record_id}")
            raise HTTPException(
                status_code=404,
                detail="LOI document not found"
            )
        elif response.status_code != 200:
            print(f"❌ EXTERNAL API ERROR: Status {response.status_code}, Response: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving LOI document: {response.text}"
            )
        
        print(f"✅ LOI DOCUMENT RETRIEVED SUCCESSFULLY")
        # Return the LOI document content
        return response.json()
        
    except ValueError as e:
        print(f"❌ SLUG PARSING ERROR: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid LOI reference format"
        )
    except requests.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to LOI service: {str(e)}"
        )
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
