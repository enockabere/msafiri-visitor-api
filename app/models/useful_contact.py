from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.models.base import Base

class UsefulContact(Base):
    __tablename__ = "useful_contacts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    department = Column(String, nullable=True)
    availability_schedule = Column(String, nullable=True)  # "24/7", "business_hours", "custom"
    availability_details = Column(Text, nullable=True)  # JSON string with detailed schedule
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String, nullable=False)
