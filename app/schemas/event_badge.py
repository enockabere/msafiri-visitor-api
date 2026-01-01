from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EventBadgeBase(BaseModel):
    badge_template_id: int
    template_variables: Dict[str, Any]

class EventBadgeCreate(EventBadgeBase):
    pass

class EventBadgeUpdate(BaseModel):
    badge_template_id: Optional[int] = None
    template_variables: Optional[Dict[str, Any]] = None

class EventBadgeResponse(EventBadgeBase):
    id: int
    event_id: int
    tenant_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ParticipantBadgeResponse(BaseModel):
    id: int
    event_badge_id: int
    participant_id: int
    badge_url: Optional[str] = None
    badge_public_id: Optional[str] = None
    issued_at: datetime

    class Config:
        from_attributes = True