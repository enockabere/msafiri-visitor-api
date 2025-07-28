from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    MT_ADMIN = "mt_admin"
    HR_ADMIN = "hr_admin"
    EVENT_ADMIN = "event_admin"
    VISITOR = "visitor"
    
class User(TenantBaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VISITOR)
    is_active = Column(Boolean, default=True)
    phone_number = Column(String(20), nullable=True)