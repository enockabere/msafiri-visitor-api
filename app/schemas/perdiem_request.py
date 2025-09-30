from pydantic import BaseModel, validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class PerdiemRequestCreate(BaseModel):
    arrival_date: date
    departure_date: date
    requested_days: Optional[int] = None
    justification: Optional[str] = None
    
    @validator('requested_days', always=True)
    def set_requested_days(cls, v, values):
        if v is None and 'arrival_date' in values and 'departure_date' in values:
            return (values['departure_date'] - values['arrival_date']).days + 1
        return v

class PerdiemRequestUpdate(BaseModel):
    requested_days: int
    justification: str

class PerdiemRequest(BaseModel):
    id: int
    participant_id: int
    arrival_date: date
    departure_date: date
    calculated_days: int
    requested_days: int
    daily_rate: Decimal
    total_amount: Decimal
    status: str
    justification: Optional[str] = None
    admin_notes: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PerdiemApprovalAction(BaseModel):
    status: str  # "approved" or "rejected"
    admin_notes: Optional[str] = None

class PerdiemPaymentAction(BaseModel):
    payment_reference: str
    admin_notes: Optional[str] = None

class ParticipantPerdiemSummary(BaseModel):
    participant_email: str
    participant_name: str
    events: list
    arrival_date: date
    departure_date: date
    calculated_days: int
    requested_days: int
    daily_rate: Decimal
    total_amount: Decimal
    can_request_perdiem: bool
    perdiem_status: Optional[str] = None