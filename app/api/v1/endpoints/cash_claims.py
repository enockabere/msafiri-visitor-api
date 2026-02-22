from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
from decimal import Decimal
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
    """Get all claims for the current user, sorted by latest first"""
    claims = db.query(Claim).filter(
        Claim.user_id == current_user.id
    ).order_by(Claim.created_at.desc()).all()
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
        status="Open",
        expense_type=claim_data.expense_type,
        payment_method=claim_data.payment_method,
        cash_pickup_date=claim_data.cash_pickup_date,
        cash_hours=claim_data.cash_hours,
        mpesa_number=claim_data.mpesa_number,
        bank_account=claim_data.bank_account,
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
    
    if claim.status not in ("draft", "Open", "Rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft/Open/Rejected claims"
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
    
    if claim.status not in ("draft", "Open", "Rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit draft/Open/Rejected claims"
        )

    claim.status = "Pending Approval"
    claim.submitted_at = datetime.utcnow()
    claim.rejection_reason = None
    claim.rejected_by = None
    claim.rejected_at = None
    
    db.commit()
    db.refresh(claim)
    
    return claim

@router.put("/{claim_id}/cancel-submission", response_model=ClaimResponse)
async def cancel_claim_submission(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel claim submission and revert to Open status"""
    from app.models.claim_approval import ClaimApproval
    
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    if claim.status != "Pending Approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel Pending Approval claims"
        )
    
    # Check if any approver has already approved or rejected
    any_action_taken = db.query(ClaimApproval).filter(
        ClaimApproval.claim_id == claim_id,
        ClaimApproval.status.in_(["APPROVED", "REJECTED"])
    ).first()
    
    if any_action_taken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel submission - approval process has already started"
        )

    claim.status = "Open"
    claim.submitted_at = None
    
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

        if not document_service.client:
            logger.warning("⚠️ Azure Document Intelligence client is None")
            return {
                "success": False,
                "message": "Receipt extraction service not initialized"
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
        logger.error(f"📷 Receipt extraction failed: {type(e).__name__}: {str(e)}")
        logger.exception("📷 Full extraction error traceback:")
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

@router.delete("/{claim_id}")
async def delete_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a claim (only Open or Pending Approval)"""
    from app.models.claim_approval import ClaimApproval
    
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )
    
    if claim.status not in ("Open", "Pending Approval"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete Open or Pending Approval claims"
        )
    
    # Delete related approvals first
    db.query(ClaimApproval).filter(ClaimApproval.claim_id == claim_id).delete()
    
    # Delete related items
    db.query(ClaimItem).filter(ClaimItem.claim_id == claim_id).delete()
    
    # Delete the claim
    db.delete(claim)
    db.commit()
    
    return {"message": "Claim deleted successfully"}

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


class ClaimItemCreate(BaseModel):
    merchant_name: str
    amount: float
    currency: str = "KES"
    date: str
    category: str
    receipt_image_url: str | None = None
    extracted_data: dict | None = None


@router.post("/{claim_id}/items")
async def add_claim_item(
    claim_id: int,
    item_data: ClaimItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an item to a claim"""
    logger.info(f"📝 add_claim_item API called: claim_id={claim_id}, merchant={item_data.merchant_name}, amount={item_data.amount}, currency={item_data.currency}")

    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )

    if claim.status not in ("draft", "Open"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add items to draft/Open claims"
        )

    # Parse date
    try:
        item_date = datetime.strptime(item_data.date, "%Y-%m-%d").date()
    except ValueError:
        item_date = datetime.utcnow().date()

    item = ClaimItem(
        claim_id=claim_id,
        merchant_name=item_data.merchant_name,
        amount=item_data.amount,
        currency=item_data.currency,
        date=item_date,
        category=item_data.category,
        receipt_image_url=item_data.receipt_image_url,
        extracted_data=item_data.extracted_data
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    # Recalculate total from all items
    total = db.query(func.sum(ClaimItem.amount)).filter(ClaimItem.claim_id == claim_id).scalar() or Decimal('0')
    claim.total_amount = total
    db.commit()

    logger.info(f"✅ Item added: id={item.id}, amount={float(item.amount)}, new_claim_total={float(total)}")

    return {
        "id": item.id,
        "claim_id": item.claim_id,
        "merchant_name": item.merchant_name,
        "amount": float(item.amount),
        "currency": item.currency,
        "date": item.date.isoformat() if item.date else None,
        "category": item.category,
        "receipt_image_url": item.receipt_image_url,
    }


@router.get("/{claim_id}/approvals")
async def get_claim_approvals(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get approval workflow for a claim"""
    from app.models.claim_approval import ClaimApproval

    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.user_id == current_user.id
    ).first()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )

    approvals = db.query(ClaimApproval).filter(
        ClaimApproval.claim_id == claim_id
    ).order_by(ClaimApproval.step_order).all()

    result = []
    for approval in approvals:
        approver = db.query(User).filter(User.id == approval.approver_user_id).first()
        result.append({
            "id": approval.id,
            "step_order": approval.step_order,
            "step_name": approval.step_name,
            "approver_user_id": approval.approver_user_id,
            "approver_name": approver.full_name if approver else "Unknown",
            "approver_email": approver.email if approver else "Unknown",
            "status": approval.status,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
        })

    return result
