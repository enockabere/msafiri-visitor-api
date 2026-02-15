"""Travel advance schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class TravelAdvanceCreate(BaseModel):
    """Schema for creating a travel advance request."""
    travel_request_id: int
    traveler_id: int
    expense_category: str = Field(..., description="visa_money, per_diem, security, or ticket")
    amount: Decimal = Field(..., gt=0, description="Amount requested")

    @validator('expense_category')
    def validate_category(cls, v):
        valid = ['visa_money', 'per_diem', 'security', 'ticket']
        if v not in valid:
            raise ValueError(f'expense_category must be one of {valid}')
        return v


class TravelAdvanceResponse(BaseModel):
    """Schema for travel advance response."""
    id: int
    travel_request_id: int
    traveler_id: int
    user_id: int
    tenant_id: int
    expense_category: str
    amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    disbursed_by: Optional[int] = None
    disbursed_at: Optional[datetime] = None
    disbursement_reference: Optional[str] = None

    class Config:
        from_attributes = True


class TravelAdvanceUpdate(BaseModel):
    """Schema for updating advance status (admin only)."""
    status: str = Field(..., description="approved, rejected, or disbursed")
    rejection_reason: Optional[str] = None
    disbursement_reference: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid = ['approved', 'rejected', 'disbursed']
        if v not in valid:
            raise ValueError(f'status must be one of {valid}')
        return v
