from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VettingMemberSelectionBase(BaseModel):
    participant_id: int
    selection: str  # 'selected', 'not_selected'
    comments: Optional[str] = None


class VettingMemberSelectionCreate(VettingMemberSelectionBase):
    pass


class VettingMemberSelectionResponse(VettingMemberSelectionBase):
    id: int
    event_id: int
    member_email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True