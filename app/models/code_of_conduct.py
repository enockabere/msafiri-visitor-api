# File: app/models/code_of_conduct.py
from sqlalchemy import Column, String, Text, Boolean, DateTime
from app.models.base import BaseModel

class CodeOfConduct(BaseModel):
    __tablename__ = "code_of_conduct"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Rich text HTML content
    url = Column(String(500), nullable=True)  # URL to external code of conduct
    tenant_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    version = Column(String(50), nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255), nullable=True)