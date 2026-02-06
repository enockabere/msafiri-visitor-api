# File: app/models/invitation.py
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Invitation(BaseModel):
    __tablename__ = "invitations"
    
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    invited_by = Column(String(255), nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    is_accepted = Column(String(10), default="false")
