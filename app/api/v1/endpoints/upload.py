from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
import os
import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_EMAIL_IMAGES_CONTAINER", "email-images")

# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    return os.path.splitext(filename)[1].lower()

def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file"""
    # Check file extension
    ext = get_file_extension(file.filename or '')
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )

async def upload_to_azure_blob(file: UploadFile, filename: str) -> str:
    """Upload file to Azure Blob Storage and return public URL"""
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        # Get container client
        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

        # Create container if it doesn't exist
        try:
            container_client.create_container(public_access='blob')
        except Exception:
            pass  # Container already exists

        # Upload file
        blob_client = container_client.get_blob_client(filename)

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # Set content type
        content_settings = ContentSettings(content_type=file.content_type)

        # Upload to blob
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=content_settings
        )

        # Return public URL
        return blob_client.url

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage SDK not installed. Please install azure-storage-blob package."
        )
    except Exception as e:
        logger.error(f"Azure blob upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image to Azure: {str(e)}"
        )

@router.post("/email-image")
async def upload_email_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image for email templates to Azure Blob Storage.

    - **file**: Image file (JPG, PNG, GIF, WEBP)
    - Returns: Public URL of the uploaded image
    """

    logger.info(f"📤 Email image upload request from user: {current_user.email}")

    # Check if Azure is configured
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage is not configured. Please set AZURE_STORAGE_CONNECTION_STRING environment variable."
        )

    # Validate file
    validate_image_file(file)

    # Generate unique filename
    ext = get_file_extension(file.filename or '')
    unique_filename = f"email-template-{uuid.uuid4()}{ext}"

    try:
        # Upload to Azure
        image_url = await upload_to_azure_blob(file, unique_filename)

        logger.info(f"✅ Image uploaded successfully: {image_url}")

        return {
            "success": True,
            "url": image_url,
            "filename": unique_filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete("/email-image/{filename}")
async def delete_email_image(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an email template image from Azure Blob Storage.

    - **filename**: Name of the file to delete
    """

    logger.info(f"🗑️ Delete email image request from user: {current_user.email}, file: {filename}")

    if not AZURE_STORAGE_CONNECTION_STRING:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage is not configured"
        )

    try:
        from azure.storage.blob import BlobServiceClient

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )

        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(filename)

        # Delete blob
        blob_client.delete_blob()

        logger.info(f"✅ Image deleted successfully: {filename}")

        return {
            "success": True,
            "message": "Image deleted successfully"
        }

    except Exception as e:
        logger.error(f"❌ Error deleting image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete image: {str(e)}"
        )
