# File: app/models/notification.py (FIXED)
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel
import enum

class NotificationType(enum.Enum):
    # FIXED: UPPERCASE to match your database
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

class NotificationPriority(enum.Enum):
    # FIXED: UPPERCASE to match your database
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class NotificationChannel(enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"

class Notification(TenantBaseModel):
    __tablename__ = "notifications"
    
    # Recipient
    user_id = Column(Integer, nullable=True)  # NULL for broadcast notifications
    user_email = Column(String(255), nullable=True)  # For external notifications
    
    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    
    # Channels
    send_in_app = Column(Boolean, default=True)
    send_email = Column(Boolean, default=False)
    send_push = Column(Boolean, default=False)
    
    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata - RENAMED to avoid SQLAlchemy reserved word
    action_url = Column(String(500), nullable=True)  # Link to relevant page
    extra_data = Column(Text, nullable=True)  # JSON data for custom fields (renamed from 'metadata')
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Who triggered this notification
    triggered_by = Column(String(255), nullable=True)