from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.sql import func
from app.db.database import Base

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
class TenantBaseModel(BaseModel):
    __abstract__ = True
    
    # This will be used for multi-tenancy
    tenant_id = Column(String, index=True, nullable=False)