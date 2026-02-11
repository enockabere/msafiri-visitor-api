# File: app/crud/notification.py (ENHANCED with edit support)
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.crud.base import CRUDBase
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User  # Added import for User model
from app.schemas.notification import NotificationCreate, NotificationUpdate

class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    
    def create_notification(
        self, 
        db: Session, 
        *, 
        notification_data: NotificationCreate
    ) -> Notification:
        """Create a notification and trigger sending"""
        notification = self.create(db, obj_in=notification_data)
        
        # Trigger sending based on channels
        self._send_notification(db, notification)
        
        return notification
    
    def create_user_notification(
        self,
        db: Session,
        *,
        user_id: int,
        title: str,
        message: str,
        tenant_id: str,
        notification_type: str = 'SYSTEM_ANNOUNCEMENT',
        priority: str = 'MEDIUM',
        send_email: bool = False,
        send_push: bool = False,
        action_url: Optional[str] = None,
        triggered_by: str
    ) -> Notification:
        """Create notification for a specific user"""
        
        # Ensure tenant_id is not None - use a default if needed
        if not tenant_id:
            tenant_id = "system"  # Default tenant for system notifications
            
        notification_data = NotificationCreate(
            user_id=user_id,
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
        return self.create_notification(db, notification_data=notification_data)
    
    def create_tenant_broadcast(
        self,
        db: Session,
        *,
        tenant_id: str,
        title: str,
        message: str,
        notification_type: str = 'SYSTEM_ANNOUNCEMENT',
        priority: str = 'MEDIUM',
        send_email: bool = False,
        send_push: bool = False,
        action_url: Optional[str] = None,
        triggered_by: str
    ) -> Notification:
        """Create broadcast notification for entire tenant"""
        notification_data = NotificationCreate(
            user_id=None,  # Broadcast to all users in tenant
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
        return self.create_notification(db, notification_data=notification_data)
    
    def get_user_notifications(
        self,
        db: Session,
        *,
        user_id: int,
        tenant_id: Optional[str],  # Can be None for super admins
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a specific user - includes chat notifications"""

        # Always filter by user to prevent cross-user data leakage
        # Users can see: their own notifications + system-wide broadcasts (tenant_id = "system")
        if tenant_id is not None and tenant_id != "system":
            # Regular users with a tenant: see their notifications + their tenant broadcasts + system broadcasts
            query = db.query(Notification).filter(
                or_(
                    # User's own notifications
                    Notification.user_id == user_id,
                    # Tenant-wide broadcasts for their tenant
                    and_(
                        Notification.user_id.is_(None),
                        Notification.tenant_id == tenant_id
                    ),
                    # System-wide broadcasts
                    and_(
                        Notification.user_id.is_(None),
                        or_(
                            Notification.tenant_id == "system",
                            Notification.tenant_id.is_(None)
                        )
                    )
                )
            )
        else:
            # Mobile users without tenant or super admins: only see their own notifications + system broadcasts
            # Do NOT show other tenants' broadcast notifications
            query = db.query(Notification).filter(
                or_(
                    # User's own notifications (regardless of tenant)
                    Notification.user_id == user_id,
                    # System-wide broadcasts only (not tenant-specific)
                    and_(
                        Notification.user_id.is_(None),
                        or_(
                            Notification.tenant_id == "system",
                            Notification.tenant_id.is_(None)
                        )
                    )
                )
            )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        return query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    
    def get_sent_notifications(
        self,
        db: Session,
        *,
        tenant_id: str,
        sent_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications sent by admins (for management)"""
        query = db.query(Notification).filter(Notification.tenant_id == tenant_id)
        
        if sent_by:
            query = query.filter(Notification.triggered_by == sent_by)
        
        return query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    
    def can_edit_notification(self, db: Session, *, notification_id: int) -> bool:
        """Check if notification can be edited (not read by anyone yet)"""
        notification = self.get(db, id=notification_id)
        if not notification:
            return False
        
        # For broadcast notifications, check if ANY user has read it
        if notification.user_id is None:
            # This is a complex query - for now, we'll allow editing broadcast notifications
            # In production, you might want to track read status per user for broadcasts
            return True
        else:
            # For individual notifications, check if the specific user has read it
            return not notification.is_read
    
    def update_notification(
        self,
        db: Session,
        *,
        notification_id: int,
        title: Optional[str] = None,
        message: Optional[str] = None,
        priority: Optional[str] = None,
        action_url: Optional[str] = None,
        updated_by: str
    ) -> Optional[Notification]:
        """Update notification if it hasn't been read"""
        notification = self.get(db, id=notification_id)
        if not notification:
            return None
        
        if not self.can_edit_notification(db, notification_id=notification_id):
            raise ValueError("Cannot edit notification that has been read")
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if message is not None:
            update_data["message"] = message
        if priority is not None:
            update_data["priority"] = priority
        if action_url is not None:
            update_data["action_url"] = action_url
        
        # Track who updated it
        update_data["triggered_by"] = f"{notification.triggered_by} (updated by {updated_by})"
        
        return self.update(db, db_obj=notification, obj_in=update_data)
    
    def delete_notification(
        self,
        db: Session,
        *,
        notification_id: int
    ) -> bool:
        """Delete notification if it hasn't been read"""
        notification = self.get(db, id=notification_id)
        if not notification:
            return False
        
        if not self.can_edit_notification(db, notification_id=notification_id):
            raise ValueError("Cannot delete notification that has been read")
        
        self.remove(db, id=notification_id)
        return True
    
    def mark_as_read(self, db: Session, *, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)
                )
            )
        ).first()
        
        if notification and not notification.is_read:
            from sqlalchemy import func
            notification.is_read = True
            notification.read_at = func.now()
            db.commit()
            db.refresh(notification)
        
        return notification
    
    def mark_all_as_read(self, db: Session, *, user_id: int, tenant_id: Optional[str]) -> int:
        """Mark all notifications as read for a user - includes chat notifications"""
        from sqlalchemy import func
        
        # Base filter for user notifications
        base_filter = and_(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None)
            ),
            Notification.is_read == False
        )
        
        # Add tenant filtering for non-mobile users
        if tenant_id is not None and tenant_id != "system":
            tenant_filter = and_(
                base_filter,
                or_(
                    Notification.tenant_id == tenant_id,
                    Notification.tenant_id == "system",
                    Notification.tenant_id.is_(None)
                )
            )
        else:
            tenant_filter = base_filter
        
        result = db.query(Notification).filter(tenant_filter).update({
            "is_read": True,
            "read_at": func.now()
        })
        
        db.commit()
        return result
    
    def get_notification_stats(self, db: Session, *, user_id: int, tenant_id: Optional[str]) -> Dict[str, Any]:
        """Get notification statistics for a user - includes chat notifications"""

        try:
            # Always filter by user to prevent cross-user data leakage
            # Users can see: their own notifications + system-wide broadcasts
            if tenant_id is not None and tenant_id != "system":
                # Regular users with a tenant
                base_query = db.query(Notification).filter(
                    or_(
                        # User's own notifications
                        Notification.user_id == user_id,
                        # Tenant-wide broadcasts for their tenant
                        and_(
                            Notification.user_id.is_(None),
                            Notification.tenant_id == tenant_id
                        ),
                        # System-wide broadcasts
                        and_(
                            Notification.user_id.is_(None),
                            or_(
                                Notification.tenant_id == "system",
                                Notification.tenant_id.is_(None)
                            )
                        )
                    )
                )
            else:
                # Mobile users without tenant or super admins
                base_query = db.query(Notification).filter(
                    or_(
                        # User's own notifications
                        Notification.user_id == user_id,
                        # System-wide broadcasts only
                        and_(
                            Notification.user_id.is_(None),
                            or_(
                                Notification.tenant_id == "system",
                                Notification.tenant_id.is_(None)
                            )
                        )
                    )
                )

            total = base_query.count()

            unread = base_query.filter(Notification.is_read == False).count()

            # Handle priority filtering safely - use string comparison
            urgent = base_query.filter(
                and_(
                    Notification.priority.in_(['URGENT', 'urgent']),
                    Notification.is_read == False
                )
            ).count()

            return {
                "total": total,
                "unread": unread,
                "urgent": urgent
            }
        except Exception as e:
            print(f"❌ Error in get_notification_stats: {str(e)}")
            print(f"📊 Parameters - user_id: {user_id}, tenant_id: {tenant_id}")
            import traceback
            traceback.print_exc()
            # Return safe defaults instead of crashing
            return {
                "total": 0,
                "unread": 0,
                "urgent": 0
            }
    
    def _send_notification(self, db: Session, notification: Notification):
        """Internal method to trigger notification sending"""
        try:
            if notification.send_email:
                # TODO: Implement email sending
                pass
            
            if notification.send_push:
                # TODO: Implement push notification
                pass
            
            # Mark as sent
            from sqlalchemy import func
            notification.sent_at = func.now()
            db.commit()
            
        except Exception as e:
            # Mark as failed
            from sqlalchemy import func
            notification.failed_at = func.now()
            notification.error_message = str(e)
            db.commit()

notification = CRUDNotification(Notification)
