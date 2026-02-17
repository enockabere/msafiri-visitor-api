"""User bank account model with encrypted sensitive data."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class UserBankAccount(Base):
    """User bank account with encrypted sensitive fields."""
    __tablename__ = "user_bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Encrypted fields (stored as encrypted strings)
    bank_name_encrypted = Column(String, nullable=False)
    account_name_encrypted = Column(String, nullable=False)
    account_number_encrypted = Column(String, nullable=False)
    branch_name_encrypted = Column(String, nullable=True)
    swift_code_encrypted = Column(String, nullable=True)
    
    # Non-sensitive fields
    currency = Column(String(10), nullable=False)  # USD, EUR, KES
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="bank_accounts")
