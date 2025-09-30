from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
import enum

class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

class AdminInvitation(BaseModel):
    __tablename__ = "admin_invitations"
    
    email = Column(String(255), nullable=False, index=True)
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")  # pending, accepted, expired, revoked
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Track if user existed before invitation
    user_existed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])