from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
from app.models.user import UserRole
import enum

class UserTenantRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    MT_ADMIN = "mt_admin"
    HR_ADMIN = "hr_admin"
    EVENT_ADMIN = "event_admin"
    FINANCE_ADMIN = "finance_admin"
    VISITOR = "visitor"
    GUEST = "guest"
    STAFF = "staff"

class UserTenant(BaseModel):
    __tablename__ = "user_tenants"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.slug"), nullable=False)
    role = Column(Enum(UserTenantRole), nullable=False, default=UserTenantRole.STAFF)
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # One tenant can be marked as primary
    
    # Tracking
    assigned_by = Column(String(255), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant")