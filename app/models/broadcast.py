from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class BroadcastType(enum.Enum):
    NEWS = "news"
    UPDATE = "update"
    ANNOUNCEMENT = "announcement"
    ALERT = "alert"

class Priority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Broadcast(BaseModel):
    __tablename__ = "broadcasts"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    broadcast_type = Column(Enum(BroadcastType), nullable=False)
    priority = Column(Enum(Priority), default=Priority.NORMAL)
    tenant_id = Column(String(50), nullable=False)
    created_by = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    
class BroadcastRead(BaseModel):
    __tablename__ = "broadcast_reads"
    
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id"), nullable=False)
    user_email = Column(String(255), nullable=False)
    read_at = Column(DateTime, nullable=False)
    
    # Relationships
    broadcast = relationship("Broadcast")