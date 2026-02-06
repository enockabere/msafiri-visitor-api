# File: app/models/inventory.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.sql import func
from app.models.base import BaseModel

class Inventory(BaseModel):
    __tablename__ = "inventory"

    tenant_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # 'stationary' or 'equipment'
    quantity = Column(Integer, default=0)
    condition = Column(String(50), default='good')  # good, fair, poor
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255))
