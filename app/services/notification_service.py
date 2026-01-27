from typing import List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_roles import UserRole as UserRoleModel
# Using existing notifications table structure
from app.models.event import Event
from app.core.email_service import email_service
import logging

logger = logging.getLogger(__name__)

def get_tenant_admins(db: Session, tenant_id: int) -> List[User]:
    """Get all admin users for a tenant"""
    from app.models.user import UserRole
    
    # Get users with admin roles in single role field using enum values
    admin_users = db.query(User).filter(
        User.tenant_id == str(tenant_id),
        User.role.in_([UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]),
        User.is_active == True
    ).all()
    
    # Get users with admin roles in relationship table
    admin_role_users = db.query(User).join(UserRoleModel).filter(
        User.tenant_id == str(tenant_id),
        UserRoleModel.role.in_(['MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN']),
        User.is_active == True
    ).all()
    
    # Combine and deduplicate
    all_admins = {user.id: user for user in admin_users + admin_role_users}
    return list(all_admins.values())

def create_notification(db: Session, user_email: str, tenant_id: str, 
                       title: str, message: str, triggered_by: str):
    """Create in-app notification using existing table structure"""
    from sqlalchemy import text
    
    db.execute(text("""
        INSERT INTO notifications (user_email, tenant_id, title, message, 
                                 notification_type, priority, send_in_app, 
                                 send_email, triggered_by, sent_at)
        VALUES (:user_email, :tenant_id, :title, :message, 
                'SYSTEM', 'MEDIUM', true, false, :triggered_by, NOW())
    """), {
        'user_email': user_email,
        'tenant_id': tenant_id,
        'title': title,
        'message': message,
        'triggered_by': triggered_by
    })

def send_event_notifications(db: Session, event: Event, action: str, created_by_email: str):
    """Send notifications to all tenant admins about event changes"""
    try:
        # Get all admin users for the tenant
        admin_users = get_tenant_admins(db, event.tenant_id)
        
        # Prepare notification content
        
        title = f"Event {action}: {event.title}"
        message = f"Event '{event.title}' has been {action} by {created_by_email}. Start date: {event.start_date}"
        
        # Send notifications to each admin
        for admin in admin_users:
            # Skip sending notification to the user who created/updated the event
            if admin.email == created_by_email:
                continue
                
            # Create in-app notification
            create_notification(
                db=db,
                user_email=admin.email,
                tenant_id=str(event.tenant_id),
                title=title,
                message=message,
                triggered_by=created_by_email
            )
            
            # Send email notification
            try:
                email_service.send_notification_email(
                    to_email=admin.email,
                    user_name=admin.full_name,
                    title=title,
                    message=f"""
                    Dear {admin.full_name},
                    
                    {message}
                    
                    Please log in to the admin portal to view more details.
                    """,
                    data={
                        'event_title': event.title,
                        'event_type': event.event_type or 'Not specified',
                        'start_date': str(event.start_date),
                        'end_date': str(event.end_date),
                        'location': event.location or 'Not specified',
                        'status': event.status
                    }
                )
                logger.info(f"Email notification sent to {admin.email} for event {event.id}")
            except Exception as e:
                logger.error(f"Failed to send email to {admin.email}: {str(e)}")
        
        db.commit()
        logger.info(f"Notifications sent for event {event.id} to {len(admin_users)} admins")
        
    except Exception as e:
        logger.error(f"Failed to send event notifications: {str(e)}")
        db.rollback()
        raise