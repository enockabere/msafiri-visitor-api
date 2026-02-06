from pydantic import BaseModel
from typing import Optional, List
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


# Comment schemas
class VettingMemberCommentCreate(BaseModel):
    participant_id: int
    comment: str


class VettingMemberCommentResponse(BaseModel):
    id: int
    event_id: int
    participant_id: int
    author_email: str
    author_name: str
    author_role: str  # 'committee_member', 'approver'
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True


class VettingMemberCommentsListResponse(BaseModel):
    participant_id: int
    comments: List[VettingMemberCommentResponse]
    total_count: int
