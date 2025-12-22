from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RoleType(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MT_ADMIN = "MT_ADMIN"
    HR_ADMIN = "HR_ADMIN"
    EVENT_ADMIN = "EVENT_ADMIN"
    STAFF = "STAFF"
    USER = "USER"
    GUEST = "GUEST"
    VOUCHER_SCANNER = "VOUCHER_SCANNER"
    VETTING_APPROVER = "VETTING_APPROVER"
    VETTING_COMMITTEE = "VETTING_COMMITTEE"

class UserRole(BaseModel):
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(RoleType), nullable=False)
    granted_by = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    granted_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    revoked_by = Column(String(255))
    
    # Relationships
    user = relationship("User")

class RoleChangeLog(BaseModel):
    __tablename__ = "role_change_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_email = Column(String(255), nullable=False)
    role = Column(Enum(RoleType), nullable=False)
    action = Column(String(20), nullable=False)  # "granted", "revoked"
    performed_by = Column(String(255), nullable=False)
    reason = Column(String(500))
    
    # Relationships
    user = relationship("User")