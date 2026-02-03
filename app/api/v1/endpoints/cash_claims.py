from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

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

router = APIRouter()
logger = logging.getLogger(__name__)

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

@router.post("/extract-receipt", response_model=ReceiptExtractionResponse)
async def extract_receipt_data(
    request: ReceiptExtractionRequest,
    current_user: User = Depends(get_current_user)
):
    """Extract data from receipt image using Azure Document Intelligence"""
    logger.info(f"📷 Receipt extraction request from user {current_user.id}: {request.image_url[:100]}...")
    
    return ReceiptExtractionResponse(
        success=False,
        message="Receipt extraction service temporarily unavailable"
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