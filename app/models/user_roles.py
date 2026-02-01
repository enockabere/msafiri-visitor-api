# File: app/models/user_roles.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class UserRole(BaseModel):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum('SUPER_ADMIN', 'MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN', 'FINANCE_ADMIN', 'VETTING_COMMITTEE', 'VETTING_APPROVER', 'PER_DIEM_APPROVER', 'VOUCHER_SCANNER', 'VISITOR', 'GUEST', 'STAFF', name='roletype'), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.slug", ondelete="CASCADE"), nullable=True, index=True)  # Tenant-specific role
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="user_roles")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    # Constraints - user can have the same role in different tenants, but only once per tenant
    __table_args__ = (
        UniqueConstraint('user_id', 'role', 'tenant_id', name='unique_user_role_tenant'),
        Index('ix_user_roles_user_tenant', 'user_id', 'tenant_id'),
    )