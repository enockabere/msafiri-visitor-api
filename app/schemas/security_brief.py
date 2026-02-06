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
    type: Optional[str] = "general"  # Maps to brief_type
    content_type: Optional[str] = "text"  # Maps to content_type enum
    content: Optional[str] = None
    document_url: Optional[str] = None
    video_url: Optional[str] = None
    event_id: Optional[int] = None
    status: Optional[str] = "published"
    publish_start_date: Optional[str] = None
    publish_end_date: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

class SecurityBriefCreate(SecurityBriefBase):
    pass

class SecurityBriefUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content_type: Optional[str] = None
    content: Optional[str] = None
    document_url: Optional[str] = None
    video_url: Optional[str] = None
    event_id: Optional[int] = None
    status: Optional[str] = None
    publish_start_date: Optional[str] = None
    publish_end_date: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
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
