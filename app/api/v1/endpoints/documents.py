from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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

# Load environment variables
load_dotenv()

router = APIRouter()

# Configure Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

print(f"DEBUG: Cloudinary config - Cloud Name: {CLOUDINARY_CLOUD_NAME}, API Key: {CLOUDINARY_API_KEY}")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document to Cloudinary using unsigned preset"""
    
    print(f"DEBUG: Upload attempt - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Validate file type
    if not file.content_type or file.content_type != 'application/pdf':
        print(f"DEBUG: Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        print(f"DEBUG: File too large: {file.size} bytes")
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        print("DEBUG: Starting Cloudinary upload...")
        print(f"DEBUG: Cloud Name: {CLOUDINARY_CLOUD_NAME}")

        # Validate Cloudinary cloud name at minimum
        if not CLOUDINARY_CLOUD_NAME:
            raise HTTPException(
                status_code=500,
                detail="Cloudinary cloud name is not configured."
            )

        # Read file content
        file_content = await file.read()

        # Create a temporary file-like object with the desired filename
        import io
        file_obj = io.BytesIO(file_content)
        file_obj.name = "code_of_conduct.pdf"  # Set the filename that Cloudinary will use

        # Use same format as working cloud.py script
        result = cloudinary.uploader.upload(
            file_obj,
            public_id="code_of_conduct",
            folder="msafiri-documents/code-of-conduct",
            resource_type="raw",  # Use raw for PDF files
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )

        print(f"DEBUG: Upload successful: {result['secure_url']}")
        print(f"DEBUG: Public ID: {result['public_id']}")
        print(f"DEBUG: Resource type: {result.get('resource_type', 'N/A')}")

        # Use the secure_url directly from Cloudinary response
        pdf_url = result["secure_url"]
        
        print(f"DEBUG: Final PDF URL: {pdf_url}")

        return {
            "success": True,
            "url": pdf_url,
            "public_id": result["public_id"],
            "format": result.get("format", "pdf"),
            "resource_type": result.get("resource_type", "image")
        }
        
    except Exception as e:
        print(f"DEBUG: Upload failed: {str(e)}")
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
    """Delete document from Cloudinary"""

    try:
        result = cloudinary.uploader.destroy(public_id)

        if result["result"] == "ok":
            return {"success": True, "message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")

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

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload avatar image to Cloudinary"""
    
    print(f"DEBUG: Avatar upload - File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
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

        # Upload avatar to Cloudinary
        result = cloudinary.uploader.upload(
            file_obj,
            folder="msafiri-documents/avatar",
            resource_type="image",
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )

        print(f"DEBUG: Avatar upload successful: {result['secure_url']}")

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result.get("format", "png")
        }
        
    except Exception as e:
        print(f"DEBUG: Avatar upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Avatar upload failed: {str(e)}")