"""Reusable passport upload and extraction endpoint using Azure Document Intelligence."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uuid
import logging
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.passport_extraction_service import passport_extraction_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_PASSPORTS_CONTAINER = os.getenv("AZURE_PASSPORTS_CONTAINER", "passports")

# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB for passport images


class PassportExtractionResponse(BaseModel):
    """Response schema for passport extraction."""
    success: bool
    file_url: str
    extracted_data: Dict[str, Any]
    message: Optional[str] = None


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return os.path.splitext(filename)[1].lower()


def validate_passport_image(file: UploadFile) -> None:
    """Validate uploaded passport image file."""
    ext = get_file_extension(file.filename or '')
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )


async def upload_to_azure_blob(content: bytes, filename: str, content_type: str) -> str:
    """Upload file to Azure Blob Storage and return public URL."""
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        container_client = blob_service_client.get_container_client(AZURE_PASSPORTS_CONTAINER)

        # Create container if it doesn't exist
        try:
            container_client.create_container(public_access='blob')
        except Exception:
            pass  # Container already exists

        blob_client = container_client.get_blob_client(filename)

        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            content,
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
            detail=f"Failed to upload image to Azure: {str(e)}"
        )


@router.post("/upload-and-extract", response_model=PassportExtractionResponse)
async def upload_and_extract_passport(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reusable passport upload and extraction endpoint.

    1. Upload image to Azure Blob Storage (passports folder)
    2. Call Azure Document Intelligence prebuilt-idDocument
    3. Return file_url + extracted_data

    This endpoint can be used by any feature that needs passport data extraction.

    Returns:
    {
        "success": true,
        "file_url": "https://blob.../passports/passport_123_timestamp.jpg",
        "extracted_data": {
            "full_name": "John Doe",
            "given_names": "John",
            "surname": "Doe",
            "date_of_birth": "1990-01-15",
            "passport_number": "AB1234567",
            "expiry_date": "2030-01-15",
            "nationality": "Kenya",
            "gender": "M",
            "issue_country": "Kenya",
            "confidence_scores": {...}
        }
    }
    """
    logger.info(f"Passport upload and extract request from user: {current_user.email}")

    # Check if Azure is configured
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage is not configured"
        )

    # Validate file
    validate_passport_image(file)

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # Generate unique filename
    ext = get_file_extension(file.filename or '.jpg')
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"passport_{current_user.id}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"

    try:
        # Upload to Azure Blob Storage
        file_url = await upload_to_azure_blob(
            content,
            unique_filename,
            file.content_type or 'image/jpeg'
        )
        logger.info(f"Passport image uploaded: {file_url}")

        # Extract data using Document Intelligence
        extracted_data = await passport_extraction_service.extract_passport_data_from_bytes(content)
        logger.info(f"Passport data extracted: {extracted_data.get('passport_number', 'N/A')}")

        return PassportExtractionResponse(
            success=True,
            file_url=file_url,
            extracted_data=extracted_data,
            message="Passport data extracted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Passport extraction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process passport: {str(e)}"
        )


@router.post("/extract-from-url")
async def extract_passport_from_url(
    url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract passport data from an existing image URL.

    Use this when the image is already uploaded to Azure Blob Storage.
    """
    logger.info(f"Passport extract from URL request from user: {current_user.email}")

    try:
        extracted_data = await passport_extraction_service.extract_passport_data(url)

        return {
            "success": True,
            "extracted_data": extracted_data,
            "message": "Passport data extracted successfully"
        }

    except Exception as e:
        logger.error(f"Passport extraction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract passport data: {str(e)}"
        )
