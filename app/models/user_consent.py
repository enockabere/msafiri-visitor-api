from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class UserConsent(BaseModel):
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String, nullable=False)
    
    # Consent details
    data_protection_accepted = Column(Boolean, default=False)
    terms_conditions_accepted = Column(Boolean, default=False)
    
    # Version tracking for audit purposes
    data_protection_version = Column(String, nullable=True)
    terms_conditions_version = Column(String, nullable=True)
    
    # Document links
    data_protection_link = Column(Text, nullable=True)
    terms_conditions_link = Column(Text, nullable=True)
    
    # Timestamps for legal compliance
    data_protection_accepted_at = Column(DateTime, nullable=True)
    terms_conditions_accepted_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="consents")