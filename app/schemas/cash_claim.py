from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class ClaimItemBase(BaseModel):
    merchant_name: Optional[str] = None
    amount: Decimal
    date: Optional[datetime] = None
    category: Optional[str] = None
    receipt_image_url: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None

class ClaimItemCreate(ClaimItemBase):
    pass

class ClaimItemResponse(ClaimItemBase):
    id: int
    claim_id: int

    class Config:
        from_attributes = True

class ClaimBase(BaseModel):
    description: Optional[str] = None
    total_amount: Optional[Decimal] = Field(default=0.0)

class ClaimCreate(ClaimBase):
    pass

class ClaimUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    total_amount: Optional[Decimal] = None

class ClaimResponse(ClaimBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    items: List[ClaimItemResponse] = []

    class Config:
        from_attributes = True

class ReceiptExtractionRequest(BaseModel):
    image_url: str

class ReceiptData(BaseModel):
    merchant_name: str
    total_amount: Decimal
    date: datetime
    items: List[Dict[str, Any]] = []
    tax_amount: Optional[Decimal] = None

class ReceiptExtractionResponse(BaseModel):
    success: bool
    extracted_data: Optional[ReceiptData] = None
    message: Optional[str] = None

class ClaimValidationRequest(BaseModel):
    claim_data: Dict[str, Any]

class ClaimValidationResponse(BaseModel):
    is_valid: bool
    validation_result: str
    suggestions: List[str] = []

class ChatMessageRequest(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    response: str
    next_step: Optional[str] = None