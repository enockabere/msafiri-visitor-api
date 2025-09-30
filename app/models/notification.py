from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class NotificationType(enum.Enum):
    USER_CREATED = "USER_CREATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    ROLE_CHANGED = "ROLE_CHANGED"
    TENANT_CREATED = "TENANT_CREATED"
    TENANT_ACTIVATED = "TENANT_ACTIVATED"
    TENANT_DEACTIVATED = "TENANT_DEACTIVATED"
    VISITOR_INVITED = "VISITOR_INVITED"
    EVENT_CREATED = "EVENT_CREATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"
    CHAT_MESSAGE = "CHAT_MESSAGE"

class NotificationStatus(enum.Enum):
    UNREAD = "unread"
    READ = "read"

class NotificationPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Notification(BaseModel):
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}
    
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), nullable=True)
    tenant_id = Column(String, nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum('USER_CREATED', 'USER_ACTIVATED', 'USER_DEACTIVATED', 'ROLE_CHANGED', 'TENANT_CREATED', 'TENANT_ACTIVATED', 'TENANT_DEACTIVATED', 'VISITOR_INVITED', 'EVENT_CREATED', 'DOCUMENT_UPLOADED', 'SYSTEM_ANNOUNCEMENT', 'CHAT_MESSAGE', name='notificationtype'), nullable=True)
    priority = Column(Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='notificationpriority'), nullable=True)
    send_in_app = Column(Boolean, default=True)
    send_email = Column(Boolean, default=False)
    send_push = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    action_url = Column(String(255), nullable=True)
    extra_data = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    triggered_by = Column(String(255), nullable=True)