from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EventSpeakerBase(BaseModel):
    name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class EventSpeakerCreate(EventSpeakerBase):
    event_id: int

class EventSpeakerUpdate(EventSpeakerBase):
    name: Optional[str] = None

class EventSpeaker(EventSpeakerBase):
    id: int
    event_id: int
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
