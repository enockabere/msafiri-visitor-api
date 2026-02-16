"""Travel advance schemas."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class TravelAdvanceCreate(BaseModel):
    """Schema for creating a travel advance request."""
    travel_request_id: int
    traveler_id: int
    expense_category: str = Field(..., description="visa_money, per_diem, security, or transport")
    amount: Decimal = Field(..., gt=0, description="Amount requested")
    currency: str = Field(default="KES", description="Currency code (e.g., KES, USD)")

    # Per diem specific
    accommodation_type: Optional[str] = Field(None, description="full_board, half_board, bed_and_breakfast, bed_only")

    # Payment details
    payment_method: str = Field(default="cash", description="cash, mpesa, or bank")
    cash_pickup_date: Optional[date] = Field(None, description="Date for cash pickup")
    cash_hours: Optional[str] = Field(None, description="morning or afternoon")
    mpesa_number: Optional[str] = Field(None, description="M-Pesa phone number")
    bank_account: Optional[str] = Field(None, description="Bank account number")

    @validator('expense_category')
    def validate_category(cls, v):
        valid = ['visa_money', 'per_diem', 'security', 'transport']
        if v not in valid:
            raise ValueError(f'expense_category must be one of {valid}')
        return v

    @validator('accommodation_type')
    def validate_accommodation_type(cls, v, values):
        if v is None:
            return v
        valid = ['full_board', 'half_board', 'bed_and_breakfast', 'bed_only']
        if v not in valid:
            raise ValueError(f'accommodation_type must be one of {valid}')
        return v

    @validator('payment_method')
    def validate_payment_method(cls, v):
        valid = ['cash', 'mpesa', 'bank']
        if v not in valid:
            raise ValueError(f'payment_method must be one of {valid}')
        return v

    @validator('cash_hours')
    def validate_cash_hours(cls, v):
        if v is None:
            return v
        valid = ['morning', 'afternoon']
        if v not in valid:
            raise ValueError(f'cash_hours must be one of {valid}')
        return v

    @validator('currency')
    def validate_currency(cls, v):
        if len(v) != 3:
            raise ValueError('currency must be a 3-letter code')
        return v.upper()


class TravelAdvanceResponse(BaseModel):
    """Schema for travel advance response."""
    id: int
    travel_request_id: int
    traveler_id: int
    user_id: int
    tenant_id: int
    expense_category: str
    amount: Decimal
    currency: str
    status: str

    # Per diem specific
    accommodation_type: Optional[str] = None

    # Payment details
    payment_method: str
    cash_pickup_date: Optional[date] = None
    cash_hours: Optional[str] = None
    mpesa_number: Optional[str] = None
    bank_account: Optional[str] = None

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

    # Computed fields from relationships
    user_name: Optional[str] = None
    approver_name: Optional[str] = None

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
