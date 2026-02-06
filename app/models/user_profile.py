from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class UserProfile(BaseModel):
    __tablename__ = "user_profiles"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    profile_image_url = Column(String(500))
    profile_image_filename = Column(String(255))
    data_deleted = Column(Boolean, default=False)
    data_deleted_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="profile")

class DataDeletionLog(BaseModel):
    __tablename__ = "data_deletion_logs"
    
    user_email = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False)
    deletion_type = Column(String(50), nullable=False)  # "personal_data", "full_account"
    tables_affected = Column(Text)  # JSON list of tables
    deletion_summary = Column(Text)
    can_restore = Column(Boolean, default=True)
