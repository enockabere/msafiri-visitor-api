# File: app/models/tenant.py (FIXED with extend_existing)
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class Tenant(BaseModel):
    __tablename__ = "tenants"
    __table_args__ = {'extend_existing': True}  # FIXED: Allow table redefinition
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    public_id = Column(String(12), unique=True, nullable=False, index=True)  # Random string for URLs
    domain = Column(String(255), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    contact_email = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # ENHANCED: Admin notification fields
    admin_email = Column(String(255), nullable=True)  # Primary admin email for notifications
    secondary_admin_emails = Column(Text, nullable=True)  # JSON array of additional admin emails
    
    # Tracking fields
    created_by = Column(String(255), nullable=True)  # Who created this tenant
    last_modified_by = Column(String(255), nullable=True)  # Who last modified
    last_notification_sent = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    allow_self_registration = Column(Boolean, default=False)
    require_admin_approval = Column(Boolean, default=True)
    max_users = Column(String(50), nullable=True)  # e.g., "unlimited", "100"
    
    # Contact information
    phone_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color code
    
    # Status tracking
    activated_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships - commented out to avoid conflicts
    # roles = relationship("Role", back_populates="tenant")
    news_updates = relationship("NewsUpdate", back_populates="tenant")
    certificate_templates = relationship("CertificateTemplate", back_populates="tenant")