from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class EventWithDuration(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    duration_days: Optional[int] = None
    perdiem_rate: Optional[Decimal] = None
    location: Optional[str] = None
    
    @validator('duration_days', always=True)
    def calculate_duration(cls, v, values):
        if 'start_date' in values and 'end_date' in values:
            start = values['start_date']
            end = values['end_date']
            return (end - start).days + 1
        return v

class ParticipantPerdiemBase(BaseModel):
    daily_rate: Decimal
    duration_days: int
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    
    @validator('total_amount', always=True)
    def calculate_total(cls, v, values):
        if 'daily_rate' in values and 'duration_days' in values:
            return values['daily_rate'] * values['duration_days']
        return v

class ParticipantPerdiem(ParticipantPerdiemBase):
    id: int
    participant_id: int
    event_id: int
    approved: bool
    paid: bool
    approved_by: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventConflict(BaseModel):
    participant_email: str
    event_id: int
    event_title: str
    conflicting_event_id: int
    conflicting_event_title: str
    conflict_type: str
    event_dates: str
    conflicting_dates: str

class ParticipantEventSummary(BaseModel):
    participant_id: int
    participant_name: str
    participant_email: str
    events: List[dict]
    total_perdiem: Decimal
    conflicts: List[EventConflict]

class PerdiemApproval(BaseModel):
    participant_id: int
    event_id: int
    approved: bool = True
    notes: Optional[str] = None

class PerdiemPayment(BaseModel):
    participant_id: int
    event_id: int
    payment_reference: str
    notes: Optional[str] = None