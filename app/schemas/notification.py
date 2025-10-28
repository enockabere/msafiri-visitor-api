# File: app/schemas/notification.py (FIXED)
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str
    priority: str = 'MEDIUM'
    send_in_app: bool = True
    send_email: bool = False
    send_push: bool = False
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None

class NotificationCreate(NotificationBase):
    user_id: Optional[int] = None
    user_email: Optional[EmailStr] = None
    tenant_id: str
    triggered_by: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None

class Notification(NotificationBase):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    tenant_id: str
    is_read: bool
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    triggered_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificationStats(BaseModel):
    total_count: int
    unread_count: int
    urgent_count: int
    by_type: Optional[Dict[str, int]] = None

class BroadcastNotification(BaseModel):
    title: str
    message: str
    priority: str = 'MEDIUM'
    send_email: bool = False
    action_url: Optional[str] = None

class UserNotification(BaseModel):
    """Send notification to specific user"""
    user_id: int
    title: str
    message: str
    priority: str = 'MEDIUM'
    send_email: bool = False
    send_push: bool = False
    action_url: Optional[str] = None

class TenantNotification(BaseModel):
    """Send notification to all users in tenant"""
    title: str
    message: str
    priority: str = 'MEDIUM'
    send_email: bool = False
    send_push: bool = False
    action_url: Optional[str] = None

class NotificationEdit(BaseModel):
    """Edit notification (if not read)"""
    title: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[str] = None
    action_url: Optional[str] = None

class NotificationWithEditInfo(Notification):
    """Notification with edit permissions"""
    can_edit: bool = False
    can_delete: bool = False