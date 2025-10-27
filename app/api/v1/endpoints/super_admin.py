from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole, UserStatus
from app.models.notification import NotificationType, NotificationPriority
from app.schemas.admin_invitations import AdminInvitationCreate, AdminInvitationResponse, AdminInvitationAccept
from app.core.email_service import email_service
from app.core.security import get_password_hash, verify_password
from app.models.user import AuthProvider
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/super-admins", response_model=List[schemas.User])
def get_super_admins(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get all super admins - only accessible by super admins"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get all users with super admin role
    super_admins = db.query(crud.user.model).filter(
        crud.user.model.role == UserRole.SUPER_ADMIN
    ).all()
    
    return super_admins

@router.post("/invite-super-admin", response_model=AdminInvitationResponse)
def invite_super_admin(
    *,
    db: Session = Depends(get_db),
    invitation_data: AdminInvitationCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Invite someone to be a super admin"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can invite other super admins"
        )
    
    # Check if user already has super admin role
    existing_user = crud.user.get_by_email(db, email=invitation_data.email)
    if existing_user and existing_user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a super admin"
        )
    
    # Check if there's already a pending invitation
    existing_invitation = crud.admin_invitation.get_by_email(db, email=invitation_data.email)
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already a pending invitation for this email"
        )
    
    # Create invitation
    user_existed = existing_user is not None
    user_id = existing_user.id if existing_user else None
    
    # If user doesn't exist, create them with default password
    if not user_existed:
        default_password = "password@1234"
        user_create = schemas.UserCreate(
            email=invitation_data.email,
            password=default_password,
            full_name=invitation_data.email.split("@")[0],
            role=UserRole.VISITOR,  # Start as visitor, will be upgraded on acceptance
            status=UserStatus.PENDING_APPROVAL,
            is_active=False,
            auth_provider=AuthProvider.LOCAL  # Ensure password gets hashed
        )
        
        new_user = crud.user.create(db, obj_in=user_create)
        user_id = new_user.id
    
    invitation = crud.admin_invitation.create_invitation(
        db,
        email=invitation_data.email,
        invited_by=current_user.email,
        user_existed=user_existed,
        user_id=user_id
    )
    
    # Send invitation email in background
    background_tasks.add_task(
        send_super_admin_invitation_email,
        invitation.email,
        invitation.invitation_token,
        current_user.full_name,
        user_existed,
        "password@1234" if not user_existed else None
    )
    
    return invitation

@router.post("/accept-invitation")
def accept_super_admin_invitation(
    *,
    db: Session = Depends(get_db),
    accept_data: AdminInvitationAccept
) -> Any:
    """Accept super admin invitation via magic link"""
    # Get invitation by token
    invitation = crud.admin_invitation.get_by_token(db, token=accept_data.token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation token"
        )
    
    # Get user (should exist since we create them during invitation)
    user = crud.user.get_by_email(db, email=invitation.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if invitation.user_existed:
        # User existed - just upgrade to super admin role
        updated_user = crud.user.update_role_with_notifications(
            db,
            user=user,
            new_role=UserRole.SUPER_ADMIN,
            changed_by=invitation.invited_by
        )
    else:
        # User was created with invitation - upgrade role and activate
        user.role = UserRole.SUPER_ADMIN
        user.status = UserStatus.ACTIVE
        user.is_active = True
        # Mark that password must be changed on first login
        user.must_change_password = True
        
        db.add(user)
        db.commit()
        db.refresh(user)
        updated_user = user
    
    # Mark invitation as accepted
    crud.admin_invitation.accept_invitation(db, invitation=invitation)
    
    return {
        "message": "Super admin invitation accepted successfully", 
        "user_id": updated_user.id,
        "must_change_password": not invitation.user_existed
    }

@router.get("/pending-invitations", response_model=List[AdminInvitationResponse])
def get_pending_invitations(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all pending super admin invitations"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    invitations = crud.admin_invitation.get_pending_invitations(db, skip=skip, limit=limit)
    return invitations

@router.post("/resend-invitation/{invitation_id}")
def resend_super_admin_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Resend super admin invitation"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    invitation = db.query(crud.admin_invitation.model).filter(
        crud.admin_invitation.model.id == invitation_id,
        crud.admin_invitation.model.status == "pending"
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed"
        )
    
    # Extend expiration by 24 hours
    from datetime import datetime, timedelta
    invitation.expires_at = datetime.utcnow() + timedelta(hours=24)
    db.add(invitation)
    db.commit()
    
    # Resend email
    background_tasks.add_task(
        send_super_admin_invitation_email,
        invitation.email,
        invitation.invitation_token,
        current_user.full_name,
        invitation.user_existed,
        "password@1234" if not invitation.user_existed else None
    )
    
    return {"message": "Invitation resent successfully"}

@router.post("/cancel-invitation/{invitation_id}")
def cancel_super_admin_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Cancel super admin invitation"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    invitation = db.query(crud.admin_invitation.model).filter(
        crud.admin_invitation.model.id == invitation_id,
        crud.admin_invitation.model.status == "pending"
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed"
        )
    
    # Mark invitation as cancelled
    invitation.status = "cancelled"
    db.add(invitation)
    db.commit()
    
    # Send cancellation email to the invited person
    background_tasks.add_task(
        send_invitation_cancelled_email,
        invitation.email,
        current_user.full_name
    )
    
    # Send notification to all super admins about the cancellation
    background_tasks.add_task(
        notify_super_admins_about_cancellation,
        db,
        invitation.email,
        current_user.full_name
    )
    
    return {"message": "Invitation cancelled successfully"}

def send_super_admin_invitation_email(email: str, token: str, invited_by: str, user_existed: bool, default_password: str = None):
    """Send super admin invitation email with magic link"""
    try:
        # Use the configured frontend URL
        from app.core.config import settings
        magic_link = f"{settings.frontend_url}/accept-invitation?token={token}"
        
        subject = "You've been invited as a Super Administrator"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #007bff;">Super Administrator Invitation</h1>
            
            <p>Hello,</p>
            
            <p>You have been invited by <strong>{invited_by}</strong> to become a Super Administrator in the MSF Msafiri system.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">What this means:</h3>
                <ul>
                    <li>You can manage all organizations and users</li>
                    <li>You can invite other super administrators</li>
                </ul>
            </div>
            
            {f"<p><strong>Note:</strong> Since you already have an account, clicking the link below will upgrade your existing account to Super Administrator.</p>" if user_existed else f"<div style='background: #e7f3ff; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;'><h3 style='margin-top: 0; color: #007bff;'>Temporary Login Details:</h3><p><strong>Email:</strong> {email}<br><strong>Password:</strong> <code style='background: #f8f9fa; padding: 4px 8px; border-radius: 3px; font-family: monospace;'>{default_password}</code></p><p style='color: #dc3545; font-weight: bold;'>Important: You must change this password on first login.</p></div>"}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{magic_link}" 
                   style="background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    Accept Invitation
                </a>
            </div>
            
            {'' if user_existed else '<p style="background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0;"><strong>First Login Process:</strong><br>1. Click "Accept Invitation" above<br>2. Login with the temporary credentials provided<br>3. You will be prompted to change your password immediately</p>'}
            
            <p><strong>Important:</strong> This invitation will expire in 24 hours.</p>
            
            <p>If you did not expect this invitation, please ignore this email.</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated notification from the MSF Msafiri System.
            </p>
        </body>
        </html>
        """
        
        email_service.send_email([email], subject, html_content)
        logger.info(f"Super admin invitation email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send super admin invitation email to {email}: {e}")

def send_invitation_cancelled_email(email: str, cancelled_by: str):
    """Send email notification about cancelled invitation"""
    try:
        subject = "Super Administrator Invitation Cancelled"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #dc3545;">Invitation Cancelled</h1>
            
            <p>Hello,</p>
            
            <p>Your invitation to become a Super Administrator in the MSF Msafiri system has been cancelled by <strong>{cancelled_by}</strong>.</p>
            
            <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <strong>Important:</strong> Any previous invitation links are now invalid and will not work.
            </div>
            
            <p>If you believe this was done in error, please contact your system administrator.</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated notification from the MSF Msafiri System.
            </p>
        </body>
        </html>
        """
        
        email_service.send_email([email], subject, html_content)
        logger.info(f"Invitation cancellation email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send cancellation email to {email}: {e}")

def notify_super_admins_about_cancellation(db: Session, cancelled_email: str, cancelled_by: str):
    """Send in-app notifications to all super admins about the cancellation"""
    try:
        # Get all super admins
        super_admins = db.query(crud.user.model).filter(
            crud.user.model.role == UserRole.SUPER_ADMIN
        ).all()
        
        # Create notification for each super admin
        for admin in super_admins:
            crud.notification.create_user_notification(
                db,
                user_id=admin.id,
                title="Invitation Cancelled",
                message=f"Super admin invitation for {cancelled_email} was cancelled by {cancelled_by}",
                tenant_id=admin.tenant_id or "system",
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                priority=NotificationPriority.MEDIUM,
                send_email=False,
                send_push=False,
                triggered_by=cancelled_by
            )
        
        logger.info(f"Sent cancellation notifications to {len(super_admins)} super admins")
        
    except Exception as e:
        logger.error(f"Failed to send notifications about cancellation: {e}")

