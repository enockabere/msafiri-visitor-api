# File: app/schemas/event.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = "Draft"
    start_date: date
    end_date: date
    location: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    banner_image: Optional[str] = None
    duration_days: Optional[int] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    banner_image: Optional[str] = None
    duration_days: Optional[int] = None

class Event(EventBase):
    id: int
    tenant_id: int
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True