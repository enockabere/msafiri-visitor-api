# File: app/models/vetting_committee.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class VettingStatus(enum.Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"

class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

class VettingCommittee(BaseModel):
    __tablename__ = "vetting_committees"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Selection period
    selection_start_date = Column(DateTime(timezone=True), nullable=False)
    selection_end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Status tracking
    status = Column(Enum(VettingStatus, values_callable=lambda obj: [e.value for e in obj]), default=VettingStatus.OPEN)
    
    # Legacy approver fields (kept for backward compatibility)
    approver_email = Column(String(255), nullable=True)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Submission tracking
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by = Column(String(255), nullable=True)
    
    # Approval tracking
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=False)
    tenant_id = Column(String, nullable=False)

    # Email template references
    email_notifications_enabled = Column(Boolean, default=False)
    selected_template_id = Column(Integer, nullable=True)
    not_selected_template_id = Column(Integer, nullable=True)

    # Reminder tracking
    reminders_sent = Column(Boolean, default=False)

    # Relationships
    event = relationship("Event")
    approver = relationship("User", foreign_keys=[approver_id])
    members = relationship("VettingCommitteeMember", back_populates="committee", cascade="all, delete-orphan")
    approvers = relationship("VettingCommitteeApprover", back_populates="committee", cascade="all, delete-orphan")
    selections = relationship("ParticipantSelection", back_populates="committee", cascade="all, delete-orphan")

class VettingCommitteeMember(BaseModel):
    __tablename__ = "vetting_committee_members"
    
    committee_id = Column(Integer, ForeignKey("vetting_committees.id"), nullable=False)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Invitation tracking
    invitation_sent = Column(Boolean, default=False)
    invitation_sent_at = Column(DateTime(timezone=True), nullable=True)
    invitation_token = Column(String(255), nullable=True)
    
    # Access tracking
    first_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)

    # Role tracking for multi-role support
    had_previous_role = Column(String(50), nullable=True)
    role_removed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    committee = relationship("VettingCommittee", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])

class VettingCommitteeApprover(BaseModel):
    __tablename__ = "vetting_committee_approvers"
    
    committee_id = Column(Integer, ForeignKey("vetting_committees.id"), nullable=False)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Invitation tracking
    invitation_sent = Column(Boolean, default=False)
    invitation_sent_at = Column(DateTime(timezone=True), nullable=True)
    invitation_token = Column(String(255), nullable=True)
    
    # Access tracking
    first_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)

    # Role tracking for multi-role support
    had_previous_role = Column(String(50), nullable=True)
    role_removed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    committee = relationship("VettingCommittee", back_populates="approvers")
    user = relationship("User", foreign_keys=[user_id])

class ParticipantSelection(BaseModel):
    __tablename__ = "participant_selections"
    
    committee_id = Column(Integer, ForeignKey("vetting_committees.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    
    # Selection decision
    selected = Column(Boolean, nullable=False)
    selection_notes = Column(Text, nullable=True)
    selected_by = Column(String(255), nullable=False)
    selected_at = Column(DateTime(timezone=True), nullable=False)
    
    # Approval override
    approver_override = Column(Boolean, default=False)
    override_notes = Column(Text, nullable=True)
    override_by = Column(String(255), nullable=True)
    override_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    committee = relationship("VettingCommittee", back_populates="selections")
    participant = relationship("EventParticipant")