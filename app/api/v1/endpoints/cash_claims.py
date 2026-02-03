from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.database import get_db
from app.models.cash_claim import Claim, ClaimItem
from app.schemas.cash_claim import (
    ClaimCreate, ClaimResponse, ClaimUpdate,
    ReceiptExtractionRequest, ReceiptExtractionResponse,
    ClaimValidationRequest, ClaimValidationResponse,
    ChatMessageRequest, ChatMessageResponse
)
from app.core.auth import get_current_user
from app.models.user import User
from app.services.azure_services import AzureDocumentIntelligenceService, AzureOpenAIService

router = APIRouter(prefix="/api/v1/cash-claims", tags=["cash-claims"])

# Initialize Azure services
document_service = AzureDocumentIntelligenceService()
openai_service = AzureOpenAIService()

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

@router.post("/extract-receipt", response_model=ReceiptExtractionResponse)
async def extract_receipt_data(
    request: ReceiptExtractionRequest,
    current_user: User = Depends(get_current_user)
):
    """Extract data from receipt image using Azure Document Intelligence"""
    try:
        extracted_data = await document_service.extract_receipt_data(request.image_url)
        
        return ReceiptExtractionResponse(
            success=True,
            extracted_data=extracted_data
        )
    
    except Exception as e:
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
    try:
        user_context = {
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_name": current_user.full_name
        }
        
        validation_result = await openai_service.validate_claim_data(
            request.claim_data,
            user_context
        )
        
        return ClaimValidationResponse(
            is_valid=True,
            validation_result=validation_result,
            suggestions=[]
        )
    
    except Exception as e:
        return ClaimValidationResponse(
            is_valid=False,
            validation_result=f"Validation failed: {str(e)}",
            suggestions=["Please check your data and try again"]
        )

@router.post("/{claim_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    claim_id: int,
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message to AI assistant"""
    try:
        # Get claim context
        claim = db.query(Claim).filter(
            Claim.id == claim_id,
            Claim.user_id == current_user.id
        ).first()
        
        context = {
            "claim_id": claim_id,
            "user_id": current_user.id,
            "claim_status": claim.status if claim else "new"
        }
        
        response = await openai_service.chat_response(request.message, context)
        
        return ChatMessageResponse(
            response=response,
            next_step="continue"
        )
    
    except Exception as e:
        return ChatMessageResponse(
            response="I'm sorry, I encountered an error. Please try again.",
            next_step="retry"
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