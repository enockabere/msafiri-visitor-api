# File: app/models/user_roles.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class UserRole(BaseModel):
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum('SUPER_ADMIN', 'MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN', 'VETTING_COMMITTEE', 'VETTING_APPROVER', 'VISITOR', 'GUEST', 'STAFF', name='roletype'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_roles")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role', name='unique_user_role'),
    )