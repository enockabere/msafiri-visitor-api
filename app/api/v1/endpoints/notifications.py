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

class RegistrationEmailRequest(BaseModel):
    to_email: str
    cc_emails: Optional[List[str]] = []
    subject: str
    message: str
    registration_url: str
    event_id: str

@router.get("/", response_model=List[schemas.Notification])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """Get current user's notifications - supports mobile users without tenants"""
    # For mobile users without tenant, get all notifications for the user
    # For tenant users, filter by tenant
    notifications = crud.notification.get_user_notifications(
        db, 
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,  # Can be None for mobile users
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

@router.get("/mobile", response_model=List[Dict[str, Any]])
def get_mobile_notifications(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    unread_only: bool = Query(False, description="Get only unread notifications"),
    skip: int = 0,
    limit: int = 20,
) -> Any:
    """Get notifications optimized for mobile app"""
    notifications = crud.notification.get_user_notifications(
        db, 
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,  # Can be None for mobile users
        unread_only=unread_only,
        skip=skip,
        limit=limit
    )
    
    # Format for mobile consumption
    result = []
    for notification in notifications:
        # Handle enum values safely
        notification_type = "general"
        if notification.notification_type:
            if hasattr(notification.notification_type, 'value'):
                notification_type = notification.notification_type.value
            else:
                notification_type = str(notification.notification_type)
        
        priority = "medium"
        if notification.priority:
            if hasattr(notification.priority, 'value'):
                priority = notification.priority.value
            else:
                priority = str(notification.priority)
        
        result.append({
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification_type,
            "priority": priority,
            "isRead": notification.is_read,
            "createdAt": notification.created_at.isoformat(),
            "readAt": notification.read_at.isoformat() if notification.read_at else None,
            "actionUrl": notification.action_url,
            "sender": notification.triggered_by
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
    """Get current user's notifications with detailed sender info - mobile friendly"""
    notifications = crud.notification.get_user_notifications(
        db, 
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,  # Can be None for mobile users
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

@router.post("/register-token")
def register_fcm_token(
    *,
    db: Session = Depends(get_db),
    token_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Register FCM token for push notifications."""
    from app.models.user import User
    
    fcm_token = token_data.get('fcm_token')
    platform = token_data.get('platform', 'unknown')
    
    if not fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FCM token is required"
        )
    
    # Update user's FCM token
    user = db.query(User).filter(User.id == current_user.id).first()
    if user:
        # Store FCM token in user record
        setattr(user, 'fcm_token', fcm_token)
        setattr(user, 'fcm_platform', platform)
        db.commit()
    
    return {"message": "FCM token registered successfully"}



@router.post("/send-registration-email")
def send_registration_email(
    *,
    email_data: RegistrationEmailRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Send registration email with clickable link"""
    try:
        from app.core.email_service import email_service
        
        # Create HTML content with clickable link
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{email_data.subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ color: #dc2626; font-size: 24px; font-weight: bold; }}
                .message {{ color: #4b5563; line-height: 1.6; margin: 20px 0; }}
                .button {{ display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🌍 MSF Event Registration</div>
                </div>
                
                <div class="message">
                    {email_data.message}
                </div>
                
                <div style="text-align: center;">
                    <a href="{email_data.registration_url}" class="button">Register Now</a>
                </div>
                
                <div class="message">
                    <p>Or copy and paste this link into your browser:</p>
                    <p><a href="{email_data.registration_url}" style="color: #dc2626;">{email_data.registration_url}</a></p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from MSF Event Registration System</p>
                    <p>Médecins Sans Frontières (MSF)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_content = f"""
        {email_data.message}
        
        Registration Link: {email_data.registration_url}
        
        ---
        This is an automated message from MSF Event Registration System
        Médecins Sans Frontières (MSF)
        """
        
        # Prepare recipient list
        recipients = [email_data.to_email]
        if email_data.cc_emails:
            recipients.extend(email_data.cc_emails)
        
        # Send email
        success = email_service.send_email(
            to_emails=recipients,
            subject=email_data.subject,
            html_content=html_content,
            text_content=text_content
        )
        
        if success:
            return {"message": "Registration email sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email"
            )
            
    except Exception as e:
        print(f"Error sending registration email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send registration email: {str(e)}"
        )

@router.post("/send-to-super-admins")
def send_notification_to_super_admins(
    *,
    db: Session = Depends(get_db),
    notification_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Send notification to all super admins"""
    print(f"🔔 Backend: Received notification request from {current_user.email}")
    print(f"📝 Backend: Notification data: {notification_data}")
    
    if current_user.role != UserRole.SUPER_ADMIN:
        print(f"❌ Backend: User {current_user.email} does not have super admin role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get all super admins
        super_admins = db.query(crud.user.model).filter(
            crud.user.model.role == UserRole.SUPER_ADMIN
        ).all()
        
        print(f"👥 Backend: Found {len(super_admins)} super admins")
        
        # Create notification for each super admin
        notifications_created = 0
        for admin in super_admins:
            print(f"📨 Backend: Creating notification for {admin.email} (ID: {admin.id})")
            from app.schemas.notification import NotificationCreate
            notification_obj = NotificationCreate(
                user_id=admin.id,
                tenant_id=admin.tenant_id or "system",
                title=notification_data.get("title", "Notification"),
                message=notification_data.get("message", ""),
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                priority=NotificationPriority.MEDIUM,
                send_in_app=True,
                send_email=False,
                send_push=False,
                triggered_by=current_user.email
            )
            notification = crud.notification.create_notification(db, notification_data=notification_obj)
            notifications_created += 1
            print(f"✅ Backend: Created notification ID {notification.id} for {admin.email}")
        
        print(f"🎉 Backend: Successfully created {notifications_created} notifications")
        return {"message": f"Notifications sent to {notifications_created} super admins"}
        
    except Exception as e:
        print(f"💥 Backend: Error creating notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}"
        )