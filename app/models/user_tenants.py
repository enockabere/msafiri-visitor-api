from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
from app.models.user import UserRole
import enum

class UserTenantRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MT_ADMIN = "MT_ADMIN"
    HR_ADMIN = "HR_ADMIN"
    EVENT_ADMIN = "EVENT_ADMIN"
    FINANCE_ADMIN = "FINANCE_ADMIN"
    VISITOR = "VISITOR"
    GUEST = "GUEST"
    STAFF = "STAFF"

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