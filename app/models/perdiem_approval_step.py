"""Per diem request approval step model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class PerdiemApprovalStep(BaseModel):
    """Track approval steps for per diem requests with workflow."""
    __tablename__ = "perdiem_approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    perdiem_request_id = Column(Integer, ForeignKey("perdiem_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_step_id = Column(Integer, ForeignKey("approval_steps.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, server_default="PENDING")  # PENDING, OPEN, APPROVED, REJECTED
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    perdiem_request = relationship("PerdiemRequest", foreign_keys=[perdiem_request_id])
    approver = relationship("User", foreign_keys=[approver_user_id])
    workflow_step = relationship("ApprovalStep", foreign_keys=[workflow_step_id])
