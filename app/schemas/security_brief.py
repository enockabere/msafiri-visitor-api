from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class BriefType(str, Enum):
    GENERAL = "general"
    EVENT_SPECIFIC = "event_specific"

class ContentType(str, Enum):
    TEXT = "text"
    VIDEO = "video"

class SecurityBriefBase(BaseModel):
    title: str
    brief_type: BriefType
    content_type: ContentType
    content: str
    event_id: Optional[int] = None

class SecurityBriefCreate(SecurityBriefBase):
    pass

class SecurityBriefUpdate(BaseModel):
    title: Optional[str] = None
    brief_type: Optional[BriefType] = None
    content_type: Optional[ContentType] = None
    content: Optional[str] = None
    event_id: Optional[int] = None
    is_active: Optional[bool] = None

class SecurityBrief(SecurityBriefBase):
    id: int
    is_active: bool
    tenant_id: str
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BriefAcknowledgment(BaseModel):
    brief_id: int
    acknowledged: bool = True

class UserBriefStatus(BaseModel):
    brief_id: int
    title: str
    brief_type: str
    content_type: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None