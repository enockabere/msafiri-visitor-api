# File: app/api/v1/endpoints/notifications.py (MINIMAL VERSION)
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.notification import NotificationPriority, NotificationType

router = APIRouter()

# Simple request models defined inline
class UserNotificationRequest(BaseModel):
    user_id: int
    title: str
    message: str
    priority: str = "medium"
    send_email: bool = False
    send_push: bool = False
    action_url: Optional[str] = None

class TenantNotificationRequest(BaseModel):
    title: str
    message: str
    priority: str = "medium"
    send_email: bool = False
    send_push: bool = False
    action_url: Optional[str] = None

class NotificationEditRequest(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[str] = None
    action_url: Optional[str] = None

class BroadcastRequest(BaseModel):
    title: str
    message: str
    priority: str = "medium"
    send_email: bool = False
    action_url: Optional[str] = None

@router.get("/", response_model=List[schemas.Notification])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """Get current user's notifications"""
    notifications = crud.notification.get_user_notifications(
        db, 
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit
    )
    return notifications

@router.get("/sent")
def get_sent_notifications(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """Get notifications sent by current admin"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    notifications = crud.notification.get_sent_notifications(
        db,
        tenant_id=tenant_context,
        sent_by=current_user.email,
        skip=skip,
        limit=limit
    )
    
    # Add edit permission info
    result = []
    for notification in notifications:
        can_edit = crud.notification.can_edit_notification(db, notification_id=notification.id)
        result.append({
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority.value if notification.priority else "medium",
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
            "triggered_by": notification.triggered_by,
            "can_edit": can_edit,
            "can_delete": can_edit,
            "user_id": notification.user_id
        })
    
    return result

@router.get("/stats", response_model=schemas.NotificationStats)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get notification statistics"""
    stats = crud.notification.get_notification_stats(
        db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    return stats

@router.post("/send-to-user", response_model=schemas.Notification)
def send_notification_to_user(
    *,
    db: Session = Depends(get_db),
    notification_data: UserNotificationRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Send notification to specific user"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Verify user exists
    target_user = crud.user.get(db, id=notification_data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Handle tenant_id - use current user's tenant if target user has None (super admin)
    target_tenant_id = target_user.tenant_id or current_user.tenant_id or tenant_context
    
    # Convert priority string to enum
    priority_map = {
        "low": NotificationPriority.LOW,
        "medium": NotificationPriority.MEDIUM,
        "high": NotificationPriority.HIGH,
        "urgent": NotificationPriority.URGENT
    }
    priority = priority_map.get(notification_data.priority.lower(), NotificationPriority.MEDIUM)
    
    notification = crud.notification.create_user_notification(
        db,
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        tenant_id=target_tenant_id,
        priority=priority,
        send_email=notification_data.send_email,
        send_push=notification_data.send_push,
        action_url=notification_data.action_url,
        triggered_by=current_user.email
    )
    
    return notification

@router.post("/send-to-tenant", response_model=schemas.Notification)
def send_notification_to_tenant(
    *,
    db: Session = Depends(get_db),
    notification_data: TenantNotificationRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Send broadcast notification to all users in tenant"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Convert priority string to enum
    priority_map = {
        "low": NotificationPriority.LOW,
        "medium": NotificationPriority.MEDIUM,
        "high": NotificationPriority.HIGH,
        "urgent": NotificationPriority.URGENT
    }
    priority = priority_map.get(notification_data.priority.lower(), NotificationPriority.MEDIUM)
    
    notification = crud.notification.create_tenant_broadcast(
        db,
        tenant_id=tenant_context,
        title=notification_data.title,
        message=notification_data.message,
        priority=priority,
        send_email=notification_data.send_email,
        send_push=notification_data.send_push,
        action_url=notification_data.action_url,
        triggered_by=current_user.email
    )
    
    return notification

@router.put("/edit/{notification_id}", response_model=schemas.Notification)
def edit_notification(
    *,
    db: Session = Depends(get_db),
    notification_id: int,
    edit_data: NotificationEditRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Edit notification if it hasn't been read"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    notification = crud.notification.get(db, id=notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Convert priority string to enum if provided
    priority = None
    if edit_data.priority:
        priority_map = {
            "low": NotificationPriority.LOW,
            "medium": NotificationPriority.MEDIUM,
            "high": NotificationPriority.HIGH,
            "urgent": NotificationPriority.URGENT
        }
        priority = priority_map.get(edit_data.priority.lower())
    
    try:
        updated_notification = crud.notification.update_notification(
            db,
            notification_id=notification_id,
            title=edit_data.title,
            message=edit_data.message,
            priority=priority,
            action_url=edit_data.action_url,
            updated_by=current_user.email
        )
        
        return updated_notification
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/delete/{notification_id}")
def delete_notification(
    *,
    db: Session = Depends(get_db),
    notification_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Delete notification if it hasn't been read"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        success = crud.notification.delete_notification(db, notification_id=notification_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return {"message": "Notification deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/mark-read/{notification_id}")
def mark_notification_read(
    *,
    db: Session = Depends(get_db),
    notification_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Mark a notification as read"""
    notification = crud.notification.mark_as_read(
        db, 
        notification_id=notification_id, 
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}

@router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Mark all notifications as read"""
    count = crud.notification.mark_all_as_read(
        db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    return {"message": f"Marked {count} notifications as read"}

@router.post("/broadcast")
def send_broadcast_notification(
    *,
    db: Session = Depends(get_db),
    broadcast_data: BroadcastRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Legacy broadcast endpoint"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Convert priority string to enum
    priority_map = {
        "low": NotificationPriority.LOW,
        "medium": NotificationPriority.MEDIUM,
        "high": NotificationPriority.HIGH,
        "urgent": NotificationPriority.URGENT
    }
    priority = priority_map.get(broadcast_data.priority.lower(), NotificationPriority.MEDIUM)
    
    notification = crud.notification.create_tenant_broadcast(
        db,
        tenant_id=tenant_context,
        title=broadcast_data.title,
        message=broadcast_data.message,
        priority=priority,
        send_email=broadcast_data.send_email,
        action_url=broadcast_data.action_url,
        triggered_by=current_user.email
    )
    
    return notification

@router.get("/detailed", response_model=List[Dict[str, Any]])
def get_my_notifications_detailed(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """Get current user's notifications with detailed sender info"""
    notifications = crud.notification.get_user_notifications(
        db, 
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit
    )
    
    # Enhance with sender details
    result = []
    for notification in notifications:
        # Get sender details
        sender_info = None
        if notification.triggered_by:
            sender = crud.user.get_by_email(db, email=notification.triggered_by)
            if sender:
                sender_info = {
                    "id": sender.id,
                    "full_name": sender.full_name,
                    "email": sender.email,
                    "role": sender.role.value
                }
        
        # Get recipient details (for user-specific notifications)
        recipient_info = None
        if notification.user_id:
            recipient = crud.user.get(db, id=notification.user_id)
            if recipient:
                recipient_info = {
                    "id": recipient.id,
                    "full_name": recipient.full_name,
                    "email": recipient.email,
                    "role": recipient.role.value
                }
        
        notification_data = {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type.value,
            "priority": notification.priority.value,
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "created_at": notification.created_at.isoformat(),
            "action_url": notification.action_url,
            "sender": sender_info,
            "recipient": recipient_info,
            "is_broadcast": notification.user_id is None,
            "tenant_id": notification.tenant_id
        }
        
        result.append(notification_data)
    
    return result