"""
Notification service for creating and sending notifications
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app import crud
from app.schemas.notification import NotificationCreate
from app.models.notification import NotificationType, NotificationPriority
from app.models.user import User, UserRole

class NotificationService:
    
    @staticmethod
    def notify_user_created(
        db: Session,
        *,
        new_user: User,
        created_by: str,
        tenant_id: str
    ):
        """Notify when a new user is created"""
        # Notify all admins in the tenant
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.MT_ADMIN, UserRole.HR_ADMIN]]
        
        for admin in admin_users:
            notification_data = NotificationCreate(
                user_id=admin.id,
                tenant_id=tenant_id,
                title="New User Created",
                message=f"User {new_user.full_name} ({new_user.email}) has been created with role {new_user.role.value}.",
                notification_type=NotificationType.USER_CREATED,
                priority=NotificationPriority.MEDIUM,
                send_in_app=True,
                send_email=True,
                action_url=f"/users/{new_user.id}",
                triggered_by=created_by
            )
            crud.notification.create_notification(db, notification_data=notification_data)
    
    @staticmethod
    def notify_role_changed(
        db: Session,
        *,
        user: User,
        old_role: UserRole,
        new_role: UserRole,
        changed_by: str,
        tenant_id: str
    ):
        """Notify when user role is changed"""
        # Notify the user whose role changed
        notification_data = NotificationCreate(
            user_id=user.id,
            tenant_id=tenant_id,
            title="Your Role Has Been Updated",
            message=f"Your role has been changed from {old_role.value} to {new_role.value} by {changed_by}.",
            notification_type=NotificationType.ROLE_CHANGED,
            priority=NotificationPriority.HIGH,
            send_in_app=True,
            send_email=True,
            action_url="/profile",
            triggered_by=changed_by
        )
        crud.notification.create_notification(db, notification_data=notification_data)
        
        # Notify admins
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.MT_ADMIN, UserRole.HR_ADMIN] and u.id != user.id]
        
        for admin in admin_users:
            admin_notification = NotificationCreate(
                user_id=admin.id,
                tenant_id=tenant_id,
                title="User Role Changed",
                message=f"{user.full_name}'s role changed from {old_role.value} to {new_role.value}.",
                notification_type=NotificationType.ROLE_CHANGED,
                priority=NotificationPriority.MEDIUM,
                send_in_app=True,
                action_url=f"/users/{user.id}",
                triggered_by=changed_by
            )
            crud.notification.create_notification(db, notification_data=admin_notification)
    
    @staticmethod
    def notify_user_status_changed(
        db: Session,
        *,
        user: User,
        action: str,  # "activated" or "deactivated"
        changed_by: str,
        tenant_id: str
    ):
        """Notify when user is activated/deactivated"""
        # Notify the user
        notification_data = NotificationCreate(
            user_id=user.id,
            tenant_id=tenant_id,
            title=f"Account {action.title()}",
            message=f"Your account has been {action} by {changed_by}.",
            notification_type=NotificationType.USER_ACTIVATED if action == "activated" else NotificationType.USER_DEACTIVATED,
            priority=NotificationPriority.HIGH,
            send_in_app=True,
            send_email=True,
            triggered_by=changed_by
        )
        crud.notification.create_notification(db, notification_data=notification_data)
    
    @staticmethod
    def notify_auto_registration(
        db: Session,
        *,
        new_user: User,
        tenant_id: str
    ):
        """Notify admins when someone auto-registers via SSO"""
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.MT_ADMIN, UserRole.HR_ADMIN]]
        
        for admin in admin_users:
            notification_data = NotificationCreate(
                user_id=admin.id,
                tenant_id=tenant_id,
                title="New Auto-Registration",
                message=f"{new_user.full_name} ({new_user.email}) has self-registered via SSO and needs approval.",
                notification_type=NotificationType.USER_CREATED,
                priority=NotificationPriority.HIGH,
                send_in_app=True,
                send_email=True,
                action_url=f"/users/pending-approvals",
                triggered_by="system"
            )
            crud.notification.create_notification(db, notification_data=notification_data)
    
    @staticmethod
    def broadcast_announcement(
        db: Session,
        *,
        title: str,
        message: str,
        tenant_id: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        send_email: bool = False,
        action_url: Optional[str] = None,
        created_by: str
    ):
        """Send broadcast notification to all users in tenant"""
        notification_data = NotificationCreate(
            user_id=None,  # Broadcast to all
            tenant_id=tenant_id,
            title=title,
            message=message,
            notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
            priority=priority,
            send_in_app=True,
            send_email=send_email,
            action_url=action_url,
            triggered_by=created_by
        )
        crud.notification.create_notification(db, notification_data=notification_data)
