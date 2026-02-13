"""Travel request approval step model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class TravelRequestApprovalStep(BaseModel):
    """Track approval steps for travel requests with workflow."""
    __tablename__ = "travel_request_approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_step_id = Column(Integer, ForeignKey("approval_steps.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, server_default="PENDING")  # PENDING, OPEN, APPROVED, REJECTED
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Budget fields required before approval
    budget_code = Column(String(100), nullable=True)
    activity_code = Column(String(100), nullable=True)
    cost_center = Column(String(100), nullable=True)
    section = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest", foreign_keys=[travel_request_id])
    approver = relationship("User", foreign_keys=[approver_user_id])
    workflow_step = relationship("ApprovalStep", foreign_keys=[workflow_step_id])
