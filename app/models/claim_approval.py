from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class ClaimApproval(Base):
    __tablename__ = "claim_approvals"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    workflow_step_id = Column(Integer, ForeignKey("approval_steps.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="PENDING")  # OPEN, PENDING, APPROVED, REJECTED
    approved_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    claim = relationship("Claim", backref="approvals")
    approver = relationship("User", foreign_keys=[approver_user_id])
    workflow_step = relationship("ApprovalStep")
