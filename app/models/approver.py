from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class ApprovalWorkflow(Base):
    __tablename__ = "approval_workflows"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    workflow_type = Column(String(50), nullable=False)  # EXPENSE_CLAIM, TRAVEL_REQUEST, etc.
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    steps = relationship("ApprovalStep", back_populates="workflow", cascade="all, delete-orphan", order_by="ApprovalStep.step_order")

class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("approval_workflows.id"), nullable=False)
    step_order = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    step_name = Column(String(255))
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workflow = relationship("ApprovalWorkflow", back_populates="steps")
    approver = relationship("User")
