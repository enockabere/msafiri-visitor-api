"""
Enhanced notification service with email integration and comprehensive triggers - FIXED VERSION
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app import crud
from app.schemas.notification import NotificationCreate
from app.models.notification import NotificationType
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant
from app.core.email_service import email_service
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def send_notification_with_email(
        db: Session,
        *,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        tenant_id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: str = "MEDIUM",
        send_email: bool = True,
        send_push: bool = False,
        action_url: Optional[str] = None,
        triggered_by: str,
        auto_send_email: bool = True
    ):
        """Create notification and automatically send email if requested"""
        notification_data = NotificationCreate(
            user_id=user_id,
            user_email=user_email,
            tenant_id=tenant_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            send_in_app=True,
            send_email=send_email,
            send_push=send_push,
            action_url=action_url,
            triggered_by=triggered_by
        )
        
        notification = crud.notification.create_notification(db, notification_data=notification_data)
    
        if send_email and auto_send_email:
            try:
                if user_id:
                    user = crud.user.get(db, id=user_id)
                    if user and user.email:
                        email_service.send_notification_email(
                            to_email=user.email,
                            user_name=user.full_name,
                            title=title,
                            message=message,
                            action_url=action_url,
                            priority=priority.lower()
                        )
                elif user_email:
                    email_service.send_notification_email(
                        to_email=user_email,
                        user_name="User",  
                        title=title,
                        message=message,
                        action_url=action_url,
                        priority=priority.lower()
                    )
            except Exception as e:
                logger.error(f"Failed to send notification email: {e}")
        
        return notification
    
    @staticmethod
    def notify_first_login_welcome(
        db: Session,
        *,
        user: User,
        tenant_id: str
    ):
        """Send welcome notification for first-time login"""
        
        tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
        tenant_name = tenant.name if tenant else tenant_id
        
        NotificationService.send_notification_with_email(
            db,
            user_id=user.id,
            tenant_id=tenant_id,
            title="Welcome to Msafiri!",
            message=f"Welcome to {tenant_name}! This is your first login. Explore the system and don't hesitate to contact administrators if you need help.",
            notification_type=NotificationType.USER_ACTIVATED,
            priority="HIGH",
            send_email=True,
            action_url="/dashboard",
            triggered_by="system"
        )

# Global notification service instance
notification_service = NotificationService()
