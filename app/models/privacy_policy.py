from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Privacy Policy")
    content = Column(Text, nullable=True)
    document_url = Column(String(500), nullable=True)
    document_public_id = Column(String(255), nullable=True)
    version = Column(String(50), nullable=True)
    effective_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(255), nullable=False)  # Email of super admin who created
    updated_by = Column(String(255), nullable=True)   # Email of super admin who last updated
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)