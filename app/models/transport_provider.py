from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class TransportProvider(BaseModel):
    __tablename__ = "transport_providers"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    provider_name = Column(String(100), nullable=False)  # "absolute_cabs", etc.
    is_enabled = Column(Boolean, default=False)
    
    # Configuration stored as JSON
    client_id = Column(String(255), nullable=True)
    client_secret = Column(Text, nullable=True)  # Encrypted
    hmac_secret = Column(Text, nullable=True)   # Encrypted
    api_base_url = Column(String(255), nullable=True)
    token_url = Column(String(255), nullable=True)
    
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")