# File: app/schemas/event.py
from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime, date
from decimal import Decimal

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = "Draft"
    start_date: date
    end_date: date
    registration_deadline: Optional[datetime] = None  # Optional field with time
    location: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    banner_image: Optional[str] = None
    duration_days: Optional[int] = None
    vendor_accommodation_id: Optional[int] = None
    expected_participants: Optional[int] = None
    accommodation_type: Optional[str] = None  # FullBoard, HalfBoard, BedAndBreakfast, BedOnly
    single_rooms: Optional[int] = None
    double_rooms: Optional[int] = None
    section: Optional[str] = None
    budget_code: Optional[str] = None
    activity_code: Optional[str] = None
    cost_center: Optional[str] = None

class EventCreate(EventBase):
    pass

from typing import Union

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    registration_deadline: Optional[Union[str, datetime]] = None  # Accept string or datetime
    location: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[Union[Decimal, float]] = None
    longitude: Optional[Union[Decimal, float]] = None
    banner_image: Optional[str] = None
    duration_days: Optional[Union[int, str]] = None      # Accept both int and str
    perdiem_rate: Optional[Decimal] = None
    perdiem_currency: Optional[str] = None
    vendor_accommodation_id: Optional[Union[int, str]] = None    # Accept both int and str
    expected_participants: Optional[Union[int, str]] = None      # Accept both int and str
    accommodation_type: Optional[str] = None  # FullBoard, HalfBoard, BedAndBreakfast, BedOnly
    single_rooms: Optional[Union[int, str]] = None               # Accept both int and str
    double_rooms: Optional[Union[int, str]] = None               # Accept both int and str
    section: Optional[str] = None
    budget_code: Optional[str] = None
    activity_code: Optional[str] = None
    cost_center: Optional[str] = None
    


class Event(EventBase):
    id: int
    tenant_id: int
    tenant_slug: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
