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

print(f"🔄 Defining extract_receipt_data endpoint...")

@router.post("/extract-receipt", response_model=ReceiptExtractionResponse)
async def extract_receipt_data(
    request: ReceiptExtractionRequest
):
    """Extract data from receipt image using Azure Document Intelligence"""
    print(f"🎯 EXTRACT RECEIPT ENDPOINT CALLED - No auth test")
    logger.info(f"🎯 EXTRACT RECEIPT ENDPOINT CALLED - No auth test")
    logger.info(f"📷 Receipt extraction request: {request.image_url[:100]}...")
    logger.info(f"📷 Azure services available: {azure_available}")
    
    # Check Azure Document Intelligence configuration
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    
    logger.info(f"📷 Azure DI Endpoint configured: {bool(endpoint)}")
    logger.info(f"📷 Azure DI API Key configured: {bool(api_key)}")
    
    if not endpoint or not api_key:
        logger.warning("⚠️ Azure Document Intelligence credentials not configured")
        return ReceiptExtractionResponse(
            success=False,
            message="Receipt extraction service not configured - Azure Document Intelligence credentials missing"
        )
    
    if not azure_available or not document_service:
        logger.warning("⚠️ Azure Document Intelligence service not available")
        return ReceiptExtractionResponse(
            success=False,
            message="Receipt extraction service temporarily unavailable - Azure services not configured"
        )
    
    try:
        logger.info("🚀 Starting Azure Document Intelligence extraction...")
        logger.info(f"🚀 Image URL: {request.image_url}")
        
        # Check if URL is accessible
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                head_response = await client.head(request.image_url)
                logger.info(f"🚀 Image URL accessible: {head_response.status_code}")
                logger.info(f"🚀 Content-Type: {head_response.headers.get('content-type')}")
                logger.info(f"🚀 Content-Length: {head_response.headers.get('content-length')}")
            except Exception as url_error:
                logger.error(f"❌ Image URL not accessible: {url_error}")
                return ReceiptExtractionResponse(
                    success=False,
                    message=f"Image URL not accessible: {str(url_error)}"
                )
        
        logger.info("🚀 Calling Azure Document Intelligence service...")
        extracted_data = await document_service.extract_receipt_data(request.image_url)
        logger.info(f"✅ Receipt extraction successful: {extracted_data}")
        
        return ReceiptExtractionResponse(
            success=True,
            extracted_data=extracted_data
        )
    
    except Exception as e:
        logger.error(f"❌ Receipt extraction failed: {str(e)}")
        logger.exception("Full exception details:")
        return ReceiptExtractionResponse(
            success=False,
            message=f"Failed to extract receipt data: {str(e)}"
        )

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