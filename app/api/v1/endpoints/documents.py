from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
import cloudinary
import cloudinary.uploader
import cloudinary.utils
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, ContentSettings
from typing import Optional

# Load environment variables
load_dotenv()

router = APIRouter()

# Configure Cloudinary (for logos and avatars)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# Configure Azure Storage (for documents)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "msafiri-documents")

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document to Azure Blob Storage"""
    
    print(f"DEBUG: Upload attempt - File: {file.filename}, Folder: {folder}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type
    if not file.content_type or file.content_type != 'application/pdf':
        print(f"DEBUG: Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        print(f"DEBUG: File too large: {file.size} bytes")
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        print("DEBUG: Starting Azure Storage upload...")

        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Use msafiri-documents container for all documents
        container_name = 'msafiri-documents'
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists
        
        # Generate blob name with timestamp and folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_prefix = folder if folder else "documents"
        blob_name = f"{folder_prefix}/{folder_prefix}_{timestamp}.pdf"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload file
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            content_settings=ContentSettings(content_type='application/pdf')
        )
        
        # Generate blob URL
        blob_url = blob_client.url
        
        print(f"DEBUG: Upload successful: {blob_url}")
        print(f"DEBUG: Blob name: {blob_name}")

        return {
            "success": True,
            "url": blob_url,
            "public_id": blob_name,
            "format": "pdf",
            "resource_type": "raw"
        }
        
    except Exception as e:
        print(f"DEBUG: Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload logo image to Cloudinary"""
    
    print(f"DEBUG: Logo upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type - accept common image formats
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files (JPEG, PNG, GIF, WEBP) are allowed")
    
    # Validate file size (5MB limit for images)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    try:
        if not CLOUDINARY_CLOUD_NAME:
            raise HTTPException(status_code=500, detail="Cloudinary cloud name is not configured.")

        # Read file content
        file_content = await file.read()
        import io
        file_obj = io.BytesIO(file_content)
        file_obj.name = file.filename

        # Upload logo to Cloudinary
        result = cloudinary.uploader.upload(
            file_obj,
            folder="msafiri-documents/logos",
            resource_type="image",
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )

        print(f"DEBUG: Logo upload successful: {result['secure_url']}")

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result.get("format", "png")
        }
        
    except Exception as e:
        print(f"DEBUG: Logo upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Logo upload failed: {str(e)}")

@router.get("/generate-signed-url/{public_id:path}")
async def generate_signed_url(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new signed URL for an existing document (for untrusted Cloudinary accounts)"""

    try:
        # Generate authenticated signed URL that expires in 7 days
        expiration_time = int((datetime.now() + timedelta(days=7)).timestamp())

        authenticated_url = cloudinary.utils.private_download_url(
            public_id,
            format="pdf",
            resource_type="raw",
            attachment=False,
            expires_at=expiration_time
        )

        return {
            "success": True,
            "url": authenticated_url,
            "expires_at": expiration_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {str(e)}")

@router.delete("/delete/{public_id:path}")
async def delete_document(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete document from Azure Blob Storage"""

    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(public_id)
        
        # Delete blob
        blob_client.delete_blob()
        
        return {"success": True, "message": "Document deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.delete("/delete-logo/{public_id:path}")
async def delete_logo(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete logo from Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        if result["result"] == "ok":
            return {"success": True, "message": "Logo deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Logo not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.delete("/delete-event-attachment/{public_id:path}")
async def delete_event_attachment(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete event attachment from Azure Blob Storage"""
    try:
        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client('msafiri-documents')
        blob_client = container_client.get_blob_client(public_id)
        
        # Delete blob
        blob_client.delete_blob()
        
        return {"success": True, "message": "Event attachment deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload avatar image to Azure Blob Storage"""
    
    print(f"DEBUG: Avatar upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type - accept common image formats
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files (JPEG, PNG, GIF, WEBP) are allowed")
    
    # Validate file size (5MB limit for images)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    try:
        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Use msafiri-documents container for all documents
        container_name = 'msafiri-documents'
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists
        
        # Generate blob name with timestamp and user ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        blob_name = f"avatar/avatar_{current_user.id}_{timestamp}{file_extension}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload file
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Generate blob URL
        blob_url = blob_client.url
        
        print(f"DEBUG: Avatar upload successful: {blob_url}")
        print(f"DEBUG: Blob name: {blob_name}")

        return {
            "success": True,
            "url": blob_url,
            "public_id": blob_name,
            "format": file_extension.replace('.', ''),
            "resource_type": "image"
        }
        
    except Exception as e:
        print(f"DEBUG: Avatar upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Avatar upload failed: {str(e)}")

@router.post("/upload-template-assets")
async def upload_template_assets(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload template assets (logos, signatures) to Azure Blob Storage"""
    
    print(f"DEBUG: Template asset upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type - accept common image formats
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files (JPEG, PNG, GIF, WEBP) are allowed")
    
    # Validate file size (5MB limit for images)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    try:
        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Use msafiri-documents container for all documents
        container_name = 'msafiri-documents'
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists
        
        # Generate blob name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
        blob_name = f"template-assets/asset_{timestamp}{file_extension}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload file
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Generate blob URL
        blob_url = blob_client.url
        
        print(f"DEBUG: Template asset upload successful: {blob_url}")
        print(f"DEBUG: Blob name: {blob_name}")

        return {
            "success": True,
            "url": blob_url,
            "public_id": blob_name,
            "format": file_extension.replace('.', ''),
            "resource_type": "image"
        }
        
    except Exception as e:
        print(f"DEBUG: Template asset upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template asset upload failed: {str(e)}")

@router.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload receipt image to Azure Blob Storage"""
    
    print(f"DEBUG: Receipt upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type - accept common image formats
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files (JPEG, PNG, GIF, WEBP) are allowed")
    
    # Validate file size (10MB limit for receipts)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Use receipts container for receipt images
        container_name = 'receipts'
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists
        
        # Generate blob name with timestamp and user ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        blob_name = f"receipt_{current_user.id}_{timestamp}{file_extension}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload file
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Generate blob URL
        blob_url = blob_client.url
        
        print(f"DEBUG: Receipt upload successful: {blob_url}")
        print(f"DEBUG: Blob name: {blob_name}")

        return {
            "success": True,
            "url": blob_url,
            "public_id": blob_name,
            "format": file_extension.replace('.', ''),
            "resource_type": "image"
        }
        
    except Exception as e:
        print(f"DEBUG: Receipt upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Receipt upload failed: {str(e)}")

@router.post("/upload-event-attachment")
async def upload_event_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload event attachment to Azure Blob Storage"""
    
    print(f"DEBUG: Event attachment upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Validate Azure Storage configuration
        if not AZURE_STORAGE_CONNECTION_STRING:
            raise HTTPException(
                status_code=500,
                detail="Azure Storage connection string is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Use msafiri-documents container for all documents
        container_name = 'msafiri-documents'
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists
        
        # Generate blob name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ''
        blob_name = f"event-attachments/attachment_{timestamp}_{file.filename}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload file
        blob_client.upload_blob(
            file_content, 
            overwrite=True, 
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Generate blob URL
        blob_url = blob_client.url
        
        print(f"DEBUG: Event attachment upload successful: {blob_url}")
        print(f"DEBUG: Blob name: {blob_name}")

        return {
            "success": True,
            "url": blob_url,
            "public_id": blob_name,
            "format": file_extension.replace('.', '') if file_extension else '',
            "resource_type": "image" if file.content_type and file.content_type.startswith('image/') else "raw",
            "file_type": file.content_type,
            "original_filename": file.filename
        }
        
    except Exception as e:
        print(f"DEBUG: Event attachment upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Event attachment upload failed: {str(e)}")
