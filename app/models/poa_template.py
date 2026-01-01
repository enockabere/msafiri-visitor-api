from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class POATemplate(BaseModel):
    """Proof of Accommodation Template - one template per vendor hotel"""
    __tablename__ = "poa_templates"

    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_content = Column(Text, nullable=False)

    # Logo and signature uploads
    logo_url = Column(String(500))
    logo_public_id = Column(String(255))
    signature_url = Column(String(500))
    signature_public_id = Column(String(255))

    # QR code toggle
    enable_qr_code = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Tenant association
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    vendor_accommodation = relationship("VendorAccommodation", back_populates="poa_template")
    tenant = relationship("Tenant")
    creator = relationship("User")
