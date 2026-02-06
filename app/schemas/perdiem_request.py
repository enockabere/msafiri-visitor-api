from pydantic import BaseModel, validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class PerdiemRequestCreate(BaseModel):
    arrival_date: date
    departure_date: date
    requested_days: Optional[int] = None
    justification: Optional[str] = None
    event_type: Optional[str] = None
    purpose: Optional[str] = None
    approver_title: Optional[str] = None
    approver_email: Optional[str] = None
    phone_number: str
    email: str
    payment_method: str  # "cash" or "mobile_money"
    cash_pickup_date: Optional[date] = None
    cash_hours: Optional[str] = None  # "morning" or "afternoon"
    mpesa_number: Optional[str] = None
    accommodation_type: Optional[str] = None  # FullBoard, HalfBoard, BedAndBreakfast, BedOnly
    accommodation_name: Optional[str] = None  # Hotel/Guesthouse name
    
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
    event_type: Optional[str] = None
    purpose: Optional[str] = None
    approver_title: Optional[str] = None
    approver_email: Optional[str] = None
    admin_notes: Optional[str] = None
    phone_number: str
    email: str
    payment_method: str
    cash_pickup_date: Optional[date] = None
    cash_hours: Optional[str] = None
    mpesa_number: Optional[str] = None
    line_manager_approved_by: Optional[str] = None
    line_manager_approved_at: Optional[datetime] = None
    budget_owner_approved_by: Optional[str] = None
    budget_owner_approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    accommodation_type: Optional[str] = None
    accommodation_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PerdiemApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None

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

class PerdiemPublicView(BaseModel):
    id: int
    participant_name: str
    participant_email: str
    event_name: str
    event_dates: str
    arrival_date: date
    departure_date: date
    requested_days: int
    daily_rate: Decimal
    total_amount: Decimal
    justification: Optional[str] = None
    event_type: Optional[str] = None
    purpose: Optional[str] = None
    approver_title: Optional[str] = None
    approver_email: Optional[str] = None
    phone_number: str
    payment_method: str
    cash_pickup_date: Optional[date] = None
    cash_hours: Optional[str] = None
    mpesa_number: Optional[str] = None
    accommodation_type: Optional[str] = None
    accommodation_name: Optional[str] = None
    status: str
    created_at: datetime
