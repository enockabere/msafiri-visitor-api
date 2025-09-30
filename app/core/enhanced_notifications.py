"""
Enhanced notification service with email integration and comprehensive triggers
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app import crud
from app.schemas.notification import NotificationCreate
from app.models.notification import NotificationType, NotificationPriority
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
        priority: NotificationPriority = NotificationPriority.MEDIUM,
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
                            priority=priority.value.lower()
                        )
                elif user_email:
                    email_service.send_notification_email(
                        to_email=user_email,
                        user_name="User",  
                        title=title,
                        message=message,
                        action_url=action_url,
                        priority=priority.value.lower()
                    )
            except Exception as e:
                logger.error(f"Failed to send notification email: {e}")
        
        return notification
    
    @staticmethod
    def notify_user_created(
        db: Session,
        *,
        new_user: User,
        created_by: str,
        tenant_id: str,
        is_first_login: bool = False
    ):
        """Notify when a new user is created + send welcome email"""
    
        tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
        tenant_name = tenant.name if tenant else tenant_id
        
        if new_user.email:
            try:
                email_service.send_welcome_email(
                    user_email=new_user.email,
                    user_name=new_user.full_name,
                    role=new_user.role.value,
                    tenant_name=tenant_name
                )
                logger.info(f"Welcome email sent to {new_user.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email to {new_user.email}: {e}")
        
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN] and u.id != new_user.id]
        
        for admin in admin_users:
            NotificationService.send_notification_with_email(
                db,
                user_id=admin.id,
                tenant_id=tenant_id,
                title="New User Created",
                message=f"User {new_user.full_name} ({new_user.email}) has been created with role {new_user.role.value}. {'This is their first login.' if is_first_login else ''}",
                notification_type=NotificationType.USER_CREATED,
                priority=NotificationPriority.MEDIUM,
                send_email=True,
                action_url=f"/users/{new_user.id}",
                triggered_by=created_by
            )
    
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
            priority=NotificationPriority.HIGH,
            send_email=True,
            action_url="/dashboard",
            triggered_by="system"
        )
    
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
        
        NotificationService.send_notification_with_email(
            db,
            user_id=user.id,
            tenant_id=tenant_id,
            title="Your Role Has Been Updated",
            message=f"Your role has been changed from {old_role.value} to {new_role.value} by {changed_by}. This may affect your access permissions.",
            notification_type=NotificationType.ROLE_CHANGED,
            priority=NotificationPriority.HIGH,
            send_email=True,
            action_url="/profile",
            triggered_by=changed_by
        )
        
        # 2. Notify admins
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN] and u.id != user.id]
        
        for admin in admin_users:
            NotificationService.send_notification_with_email(
                db,
                user_id=admin.id,
                tenant_id=tenant_id,
                title="User Role Changed",
                message=f"{user.full_name}'s role changed from {old_role.value} to {new_role.value} by {changed_by}.",
                notification_type=NotificationType.ROLE_CHANGED,
                priority=NotificationPriority.MEDIUM,
                send_email=True,
                action_url=f"/users/{user.id}",
                triggered_by=changed_by
            )
    
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
        
        notification_type = NotificationType.USER_ACTIVATED if action == "activated" else NotificationType.USER_DEACTIVATED
        priority = NotificationPriority.HIGH if action == "activated" else NotificationPriority.MEDIUM
        
        # 1. Notify the user
        NotificationService.send_notification_with_email(
            db,
            user_id=user.id,
            tenant_id=tenant_id,
            title=f"Account {action.title()}",
            message=f"Your account has been {action} by {changed_by}. {'You can now access the system.' if action == 'activated' else 'Please contact your administrator if you have questions.'}",
            notification_type=notification_type,
            priority=priority,
            send_email=True,
            triggered_by=changed_by
        )
        
        # 2. Notify admins
        admin_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
        admin_users = [u for u in admin_users if u.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN] and u.id != user.id]
        
        for admin in admin_users:
            NotificationService.send_notification_with_email(
                db,
                user_id=admin.id,
                tenant_id=tenant_id,
                title=f"User {action.title()}",
                message=f"{user.full_name} ({user.email}) has been {action} by {changed_by}.",
                notification_type=notification_type,
                priority=NotificationPriority.MEDIUM,
                send_email=True,
                action_url=f"/users/{user.id}",
                triggered_by=changed_by
            )
    
    @staticmethod
    def notify_tenant_created(
        db: Session,
        *,
        tenant: Tenant,
        created_by: str
    ):
        """Notify when a new tenant is created"""
        
        # Get all super admins (they manage tenants)
        super_admins = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).all()
        
        # Send email to all super admins
        super_admin_emails = [admin.email for admin in super_admins if admin.email]
        if super_admin_emails:
            try:
                email_service.send_tenant_notification_email(
                    to_emails=super_admin_emails,
                    title=f"New Tenant Created: {tenant.name}",
                    message=f"A new tenant '{tenant.name}' has been created by {created_by}. Slug: {tenant.slug}",
                    tenant_name=tenant.name,
                    action_type="created"
                )
            except Exception as e:
                logger.error(f"Failed to send tenant creation emails: {e}")
        
        # Create in-app notifications for super admins
        for admin in super_admins:
            NotificationService.send_notification_with_email(
                db,
                user_id=admin.id,
                tenant_id="system",  # System-level notification
                title="New Tenant Created",
                message=f"Tenant '{tenant.name}' (slug: {tenant.slug}) has been created by {created_by}. Contact: {tenant.contact_email}",
                notification_type=NotificationType.TENANT_CREATED,
                priority=NotificationPriority.HIGH,
                send_email=False,  # Already sent above
                action_url=f"/tenants/{tenant.id}",
                triggered_by=created_by,
                auto_send_email=False  # Prevent duplicate emails
            )
    
    @staticmethod
    def notify_tenant_status_changed(
        db: Session,
        *,
        tenant: Tenant,
        action: str,  # "activated" or "deactivated"
        changed_by: str
    ):
        """Notify when tenant is activated/deactivated"""
        
        notification_type = NotificationType.TENANT_ACTIVATED if action == "activated" else NotificationType.TENANT_DEACTIVATED
        
        # 1. Notify all super admins
        super_admins = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).all()
        
        super_admin_emails = [admin.email for admin in super_admins if admin.email]
        if super_admin_emails:
            try:
                email_service.send_tenant_notification_email(
                    to_emails=super_admin_emails,
                    title=f"Tenant {action.title()}: {tenant.name}",
                    message=f"Tenant '{tenant.name}' has been {action} by {changed_by}.",
                    tenant_name=tenant.name,
                    action_type=action
                )
            except Exception as e:
                logger.error(f"Failed to send tenant {action} emails: {e}")
        
        for admin in super_admins:
            NotificationService.send_notification_with_email(
                db,
                user_id=admin.id,
                tenant_id="system",
                title=f"Tenant {action.title()}",
                message=f"Tenant '{tenant.name}' has been {action} by {changed_by}.",
                notification_type=notification_type,
                priority=NotificationPriority.HIGH,
                send_email=False,  # Already sent above
                action_url=f"/tenants/{tenant.id}",
                triggered_by=changed_by,
                auto_send_email=False
            )
        
        # 2. Notify all users in the affected tenant
        if action == "deactivated":
            tenant_users = crud.user.get_by_tenant(db, tenant_id=tenant.slug)
            for user in tenant_users:
                NotificationService.send_notification_with_email(
                    db,
                    user_id=user.id,
                    tenant_id=tenant.slug,
                    title="Organization Deactivated",
                    message=f"Your organization '{tenant.name}' has been temporarily deactivated. Please contact support for more information.",
                    notification_type=NotificationType.TENANT_DEACTIVATED,
                    priority=NotificationPriority.URGENT,
                    send_email=True,
                    triggered_by=changed_by
                )
    
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
        
        # Create the broadcast notification
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
        notification = crud.notification.create_notification(db, notification_data=notification_data)
        
        # If email is requested, send to all users in tenant
        if send_email:
            tenant_users = crud.user.get_by_tenant(db, tenant_id=tenant_id)
            user_emails = [user.email for user in tenant_users if user.email and user.is_active]
            
            if user_emails:
                try:
                    # Send individual emails for better personalization
                    for user in tenant_users:
                        if user.email and user.is_active:
                            email_service.send_notification_email(
                                to_email=user.email,
                                user_name=user.full_name,
                                title=title,
                                message=message,
                                action_url=action_url,
                                priority=priority.value.lower()
                            )
                    logger.info(f"Broadcast emails sent to {len(user_emails)} users in tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to send broadcast emails to tenant {tenant_id}: {e}")
        
        return notification

# Global notification service instance
notification_service = NotificationService()