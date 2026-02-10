from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class ClaimItemBase(BaseModel):
    merchant_name: Optional[str] = None
    amount: Decimal
    currency: Optional[str] = "KES"
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
    currency: Optional[str] = "KES"
    expense_type: Optional[str] = None
    payment_method: Optional[str] = None
    cash_pickup_date: Optional[datetime] = None
    cash_hours: Optional[str] = None
    mpesa_number: Optional[str] = None
    bank_account: Optional[str] = None

class ClaimCreate(ClaimBase):
    pass

class ClaimUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    expense_type: Optional[str] = None
    payment_method: Optional[str] = None
    cash_pickup_date: Optional[datetime] = None
    cash_hours: Optional[str] = None
    mpesa_number: Optional[str] = None
    bank_account: Optional[str] = None

class ClaimResponse(ClaimBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    items: List[ClaimItemResponse] = []

    @field_serializer('approved_by', 'rejected_by')
    def serialize_user_ids(self, value: Optional[int]) -> Optional[str]:
        return str(value) if value is not None else None

    class Config:
        from_attributes = True

class ClaimApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None

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
