from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class PerDiemSetup(BaseModel):
    __tablename__ = "perdiem_setup"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    daily_rate = Column(Numeric(10,2), nullable=False)
    currency = Column(String(10), nullable=False)
    modified_by = Column(String(255), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="perdiem_setup")
