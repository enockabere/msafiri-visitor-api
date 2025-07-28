from sqlalchemy import Column, String, Boolean, Text
from app.models.base import BaseModel

class Tenant(BaseModel):
    __tablename__ = "tenants"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    contact_email = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)