from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging
import os

from app.db.database import get_db
from app.models.cash_claim import Claim, ClaimItem
from app.schemas.cash_claim import (
    ClaimCreate, ClaimResponse, ClaimUpdate,
    ReceiptExtractionRequest, ReceiptExtractionResponse,
    ClaimValidationRequest, ClaimValidationResponse,
    ChatMessageRequest, ChatMessageResponse
)
from pydantic import BaseModel

class ImageUrlRequest(BaseModel):
    image_url: str
from app.api.deps import get_current_user
from app.models.user import User

# Try to import Azure services
print("🔄 Starting Azure services import...")
try:
    from app.services.azure_services import AzureDocumentIntelligenceService, AzureOpenAIService
    print("✅ Azure services modules imported")
    document_service = AzureDocumentIntelligenceService()
    print("✅ Document Intelligence service initialized")
    openai_service = AzureOpenAIService()
    print("✅ OpenAI service initialized")
    azure_available = True
    print("✅ Azure services imported and initialized successfully")
except Exception as e:
    print(f"❌ Failed to import or initialize Azure services: {e}")
    import traceback
    print(f"❌ Full traceback: {traceback.format_exc()}")
    document_service = None
    openai_service = None
    azure_available = False

print(f"🔄 Cash claims module loading complete. Azure available: {azure_available}")

router = APIRouter()
logger = logging.getLogger(__name__)
print(f"🔄 Cash claims router and logger initialized")

# Initialize Azure services
# document_service = AzureDocumentIntelligenceService()
# openai_service = AzureOpenAIService()

@router.get("/", response_model=List[ClaimResponse])
async def get_user_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all claims for the current user"""
    claims = db.query(Claim).filter(Claim.user_id == current_user.id).all()
    return claims

@router.post("/", response_model=ClaimResponse)
async def create_claim(
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new claim"""
    claim = Claim(
        user_id=current_user.id,
        description=claim_data.description,
        total_amount=claim_data.total_amount or 0.0,
        status="draft"
    )
    
    db.add(claim)
    db.commit()
    db.refresh(claim)
    
    return claim

@router.put("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    claim_id: int,
    claim_data: ClaimUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a claim"""
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    if claim.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft claims"
        )
    
    for field, value in claim_data.dict(exclude_unset=True).items():
        setattr(claim, field, value)
    
    db.commit()
    db.refresh(claim)
    
    return claim

@router.put("/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a claim for approval"""
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    if claim.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit draft claims"
        )
    
    claim.status = "pending"
    claim.submitted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(claim)
    
    return claim

print(f"🔄 Defining test endpoint...")

@router.get("/test-endpoint")
async def test_endpoint():
    """Simple test endpoint to verify routing works"""
    print("🎯 TEST ENDPOINT CALLED")
    logger.info("🎯 TEST ENDPOINT CALLED")
    return {"message": "Cash claims routing works!", "timestamp": datetime.utcnow().isoformat()}

@router.get("/test-auth")
async def test_auth_endpoint(current_user: User = Depends(get_current_user)):
    """Test endpoint with authentication"""
    print(f"🎯 TEST AUTH ENDPOINT CALLED - User: {current_user.id}")
    logger.info(f"🎯 TEST AUTH ENDPOINT CALLED - User: {current_user.id}")
    return {"message": "Authentication works!", "user_id": current_user.id, "timestamp": datetime.utcnow().isoformat()}

print(f"🔄 Defining simple GET test endpoint...")

@router.get("/working-test")
def working_test():
    """Simple GET endpoint that should definitely work"""
    print("🎯 WORKING TEST ENDPOINT CALLED")
    return {"message": "This endpoint works!", "timestamp": datetime.utcnow().isoformat()}

@router.post("/test-receipt-upload")
async def test_receipt_upload(request: dict):
    """Test receipt extraction with a direct image URL"""
    logger.info(f"🎯 TEST RECEIPT UPLOAD CALLED")
    
    image_url = request.get('image_url')
    if not image_url:
        return {"success": False, "message": "image_url is required in request body"}
    
    logger.info(f"📷 Image URL: {image_url}")
    
    if not azure_available or not document_service:
        return {
            "success": False,
            "message": "Azure Document Intelligence service not available",
            "azure_available": azure_available
        }
    
    try:
        logger.info(f"📷 Starting receipt extraction...")
        extracted_data = await document_service.extract_receipt_data(image_url)
        logger.info(f"📷 Extraction successful: {extracted_data}")
        
        return {
            "success": True,
            "message": "Receipt extracted successfully",
            "image_url": image_url,
            "extracted_data": extracted_data
        }
    except Exception as e:
        logger.error(f"📷 Receipt extraction failed: {str(e)}")
        return {
            "success": False,
            "message": f"Receipt extraction failed: {str(e)}",
            "image_url": image_url
        }

@router.post("/minimal-test")
def minimal_test_post(data: dict):
    """Absolutely minimal POST test"""
    return {"received": data, "status": "working"}

print(f"🔄 Defining extract_receipt_data endpoint...")

@router.post("/extract-receipt-no-auth")
async def extract_receipt_data_no_auth(request: ImageUrlRequest):
    """Extract data from receipt image - no auth version for testing"""
    try:
        logger.info(f"🎯 EXTRACT RECEIPT NO AUTH CALLED")
        logger.info(f"📷 Image URL: {request.image_url}")
        
        if not azure_available or not document_service:
            logger.warning("⚠️ Azure Document Intelligence service not available")
            return {
                "success": False,
                "message": "Receipt extraction service temporarily unavailable - Azure services not configured"
            }
        
        logger.info(f"📷 Starting receipt extraction for: {request.image_url}")
        extracted_data = await document_service.extract_receipt_data(request.image_url)
        logger.info(f"📷 Extraction successful: {extracted_data}")
        
        return {
            "success": True,
            "message": "Receipt extracted successfully",
            "image_url": request.image_url,
            "extracted_data": extracted_data
        }
    except Exception as e:
        logger.error(f"📷 Receipt extraction failed: {str(e)}")
        return {
            "success": False,
            "message": f"Receipt extraction failed: {str(e)}"
        }

@router.post("/validate", response_model=ClaimValidationResponse)
async def validate_claim_data(
    request: ClaimValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate claim data using AI"""
    return ClaimValidationResponse(
        is_valid=True,
        validation_result="Validation service temporarily unavailable",
        suggestions=[]
    )

@router.post("/{claim_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    claim_id: int,
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message to AI assistant"""
    return ChatMessageResponse(
        response="AI chat service is temporarily unavailable.",
        next_step="continue"
    )

@router.get("/{claim_id}/chat")
async def get_chat_messages(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for a claim (placeholder for future implementation)"""
    return {"messages": []}

@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific claim"""
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    return claim