from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class CountryTravelRequirement(BaseModel):
    __tablename__ = "country_travel_requirements"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    country = Column(String(100), nullable=False)  # Country name
    visa_required = Column(Boolean, default=False)
    eta_required = Column(Boolean, default=False)
    passport_required = Column(Boolean, default=True)
    flight_ticket_required = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255), nullable=True)
    
    # Ensure unique combination of tenant and country
    __table_args__ = (
        UniqueConstraint('tenant_id', 'country', name='unique_tenant_country'),
    )
    
    # Relationships
    tenant = relationship("Tenant")