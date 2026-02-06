from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class PerDiemSetup(BaseModel):
    __tablename__ = "perdiem_setup"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    daily_rate = Column(Numeric(10,2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    modified_by = Column(String(255), nullable=True)

    # Accommodation deduction rates (to subtract from daily per diem)
    fullboard_rate = Column(Numeric(10,2), nullable=True, default=0)  # Full Board rate per day
    halfboard_rate = Column(Numeric(10,2), nullable=True, default=0)  # Half Board rate per day
    bed_and_breakfast_rate = Column(Numeric(10,2), nullable=True, default=0)  # B&B rate per day
    bed_only_rate = Column(Numeric(10,2), nullable=True, default=0)  # Bed Only rate per day

    # Relationships
    tenant = relationship("Tenant", back_populates="perdiem_setup")
