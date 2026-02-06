from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class TravelAgent(BaseModel):
    __tablename__ = "travel_agents"
    
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), nullable=False)
    created_by = Column(String(255), nullable=False)
    
    # API access token for limited access
    api_token = Column(String(255), unique=True)
