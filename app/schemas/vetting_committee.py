# File: app/schemas/vetting_committee.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models.vetting_committee import VettingStatus, ApprovalStatus

class VettingCommitteeMemberCreate(BaseModel):
    email: EmailStr
    full_name: str

class VettingCommitteeMemberResponse(BaseModel):
    id: int
    email: str
    full_name: str
    invitation_sent: bool
    invitation_sent_at: Optional[datetime]
    first_login: Optional[datetime]
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True

class VettingCommitteeApproverCreate(BaseModel):
    email: EmailStr
    full_name: str

class VettingCommitteeApproverResponse(BaseModel):
    id: int
    email: str
    full_name: str
    invitation_sent: bool
    invitation_sent_at: Optional[datetime]
    first_login: Optional[datetime]
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True

class VettingCommitteeCreate(BaseModel):
    event_id: int
    selection_start_date: datetime
    selection_end_date: datetime
    approver_email: Optional[EmailStr] = None  # Legacy field for backward compatibility
    approvers: List[VettingCommitteeApproverCreate] = []  # New field for multiple approvers
    members: List[VettingCommitteeMemberCreate]

class VettingCommitteeResponse(BaseModel):
    id: int
    event_id: int
    selection_start_date: datetime
    selection_end_date: datetime
    status: VettingStatus
    approver_email: Optional[str] = None  # Legacy field
    approval_status: ApprovalStatus
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    members: List[VettingCommitteeMemberResponse]
    approvers: List[VettingCommitteeApproverResponse] = []  # New field
    
    class Config:
        from_attributes = True

class ParticipantSelectionCreate(BaseModel):
    participant_id: int
    selected: bool
    selection_notes: Optional[str] = None

class ParticipantSelectionResponse(BaseModel):
    id: int
    participant_id: int
    selected: bool
    selection_notes: Optional[str]
    selected_by: str
    selected_at: datetime
    approver_override: bool
    override_notes: Optional[str]
    
    class Config:
        from_attributes = True

class VettingSubmissionRequest(BaseModel):
    selections: List[ParticipantSelectionCreate]

class ApprovalDecisionRequest(BaseModel):
    approval_status: ApprovalStatus
    approval_notes: Optional[str] = None
    participant_overrides: Optional[List[ParticipantSelectionCreate]] = None