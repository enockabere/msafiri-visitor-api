# File: app/models/role.py
from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Role(BaseModel):
    __tablename__ = "roles"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.slug"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Relationship to tenant
    tenant = relationship("Tenant")
