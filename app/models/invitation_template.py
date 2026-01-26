from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class InvitationTemplate(BaseModel):
    __tablename__ = "invitation_templates"

    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_content = Column(Text, nullable=False)
    logo_url = Column(String(500))
    logo_public_id = Column(String(255))
    watermark_url = Column(String(500))
    watermark_public_id = Column(String(255))
    signature_url = Column(String(500))
    signature_public_id = Column(String(255))
    enable_qr_code = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    address_fields = Column(JSON)
    signature_footer_fields = Column(JSON)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="invitation_templates")