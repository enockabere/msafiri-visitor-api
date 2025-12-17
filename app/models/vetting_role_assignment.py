# File: app/models/vetting_role_assignment.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class VettingRoleAssignment(BaseModel):
    __tablename__ = "vetting_role_assignments"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    committee_id = Column(Integer, ForeignKey("vetting_committees.id", ondelete="CASCADE"), nullable=False)
    role_type = Column(String(50), nullable=False)
    removed_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User")
    committee = relationship("VettingCommittee")
