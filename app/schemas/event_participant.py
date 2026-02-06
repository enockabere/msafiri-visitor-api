from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.event_participant import ParticipantRole, ParticipantStatus

class EventParticipantBase(BaseModel):
    full_name: str
    email: str
    role: Optional[str] = "attendee"

class EventParticipantCreate(EventParticipantBase):
    pass

class EventParticipantUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None

class EventParticipant(EventParticipantBase):
    id: int
    event_id: int
    status: str
    invited_by: str
    participant_role: Optional[str] = None
    participant_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
