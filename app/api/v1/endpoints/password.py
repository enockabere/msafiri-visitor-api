from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.core.security import get_password_hash, verify_password
from app.core.email_service import email_service
from app.core.config import settings
from app.models.user import User, AuthProvider
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def generate_reset_token() -> str:
    """Generate a secure reset token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def send_password_reset_email(user: User, reset_token: str) -> bool:
    """Send password reset email with dynamic frontend URL"""
    
    # FIXED: Use dynamic frontend URL based on environment
    frontend_url = settings.frontend_url
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"
    
    # Log for debugging
    logger.info(f"Sending password reset email to {user.email} with URL: {reset_url}")
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #dc3545;">Password Reset Request</h1>
        </div>
        
        <p>Hello {user.full_name},</p>
        
        <p>You have requested to reset your password for your Msafiri account.</p>
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <p style="margin: 0;"><strong>Account Details:</strong></p>
            <ul style="margin: 10px 0;">
                <li><strong>Email:</strong> {user.email}</li>
                <li><strong>Name:</strong> {user.full_name}</li>
            </ul>
        </div>
        
        <p>Click the button below to reset your password. This link will expire in 1 hour.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" 
               style="background: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Reset My Password
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_url}">{reset_url}</a>
        </p>
        
        <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
            <p style="margin: 0; color: #721c24;"><strong>Security Notice:</strong></p>
            <p style="margin: 5px 0 0 0; color: #721c24;">
                If you didn't request this password reset, please ignore this email. 
                Your password will remain unchanged.
            </p>
        </div>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        
        <p style="color: #666; font-size: 14px;">
            This reset link will expire in 1 hour for security reasons.<br>
            Environment: {settings.ENVIRONMENT}<br>
            Frontend URL: {frontend_url}
        </p>
        
        <p style="color: #666; font-size: 12px;">
            Best regards,<br>
            Msafiri Team
        </p>
    </body>
    </html>
    """
    
    try:
        return email_service.send_email(
            to_emails=[user.email],
            subject="Reset Your Msafiri Password",
            html_content=html_content
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return False

@router.post("/request-reset")
def request_password_reset(
    *,
    db: Session = Depends(get_db),
    reset_request: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks
) -> Any:
    """
    Request password reset - sends reset token via email
    """
    # Find user by email (LOCAL auth only)
    user = crud.user.get_by_email(db, email=reset_request.email)
    
    # Always return success to prevent email enumeration attacks
    success_response = {
        "message": "If an account with that email exists, a password reset link has been sent.",
        "status": "success"
    }
    
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {reset_request.email}")
        return success_response
    
    if user.auth_provider != AuthProvider.LOCAL:
        logger.warning(f"Password reset requested for SSO user: {reset_request.email}")
        return {
            "message": "This account uses Single Sign-On (SSO). Please contact your administrator to reset your password.",
            "status": "sso_user"
        }
    
    if not user.is_active:
        logger.warning(f"Password reset requested for inactive user: {reset_request.email}")
        return success_response
    
    # Generate reset token
    reset_token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Save token to database
    update_data = {
        "password_reset_token": reset_token,
        "password_reset_expires": expires_at
    }
    crud.user.update(db, db_obj=user, obj_in=update_data)
    
    # Send email in background
    background_tasks.add_task(send_password_reset_email, user, reset_token)
    
    logger.info(f"Password reset token generated for user: {user.email}")
    
    return success_response

@router.get("/verify-reset-token")
def verify_reset_token(
    *,
    db: Session = Depends(get_db),
    token: str
) -> Any:
    """
    Verify if a reset token is valid
    """
    if not token or len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format"
        )
    
    # Find user with this token
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(
        User.password_reset_token == token,
        User.password_reset_expires > now
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not active"
        )
    
    # Handle timezone for expiry calculation
    expires_at = user.password_reset_expires
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return {
        "message": "Token is valid",
        "user_email": user.email,
        "user_name": user.full_name,
        "expires_in_minutes": int((expires_at - now).total_seconds() / 60)
    }

@router.post("/reset-password")
def reset_password(
    *,
    db: Session = Depends(get_db),
    reset_data: schemas.PasswordResetConfirm
) -> Any:
    """
    Reset password using valid token
    """
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    if len(reset_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Find user with valid token
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(
        User.password_reset_token == reset_data.token,
        User.password_reset_expires > now
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not active"
        )
    
    # Update password and clear reset token
    from sqlalchemy import func
    update_data = {
        "hashed_password": get_password_hash(reset_data.new_password),
        "password_reset_token": None,
        "password_reset_expires": None,
        "password_changed_at": func.now()
    }
    
    updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
    
    logger.info(f"Password successfully reset for user: {user.email}")
    
    # Send confirmation email
    try:
        confirmation_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #28a745;">Password Successfully Reset</h1>
            </div>
            
            <p>Hello {user.full_name},</p>
            
            <p>Your password has been successfully reset for your Msafiri account.</p>
            
            <div style="background: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0; color: #155724;"><strong>Security Confirmation:</strong></p>
                <p style="margin: 5px 0 0 0; color: #155724;">
                    Your password was changed on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}.
                </p>
            </div>
            
            <p>You can now log in to Msafiri using your new password.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{settings.FRONTEND_URL}/login" 
                   style="background: #28a745; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Login to Msafiri
                </a>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>Security Tip:</strong></p>
                <p style="margin: 5px 0 0 0; color: #856404;">
                    If you didn't reset this password, please contact your administrator immediately.
                </p>
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 12px;">
                Best regards,<br>
                Msafiri Team
            </p>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_emails=[user.email],
            subject="Password Reset Confirmation - Msafiri",
            html_content=confirmation_html
        )
        
    except Exception as e:
        logger.error(f"Failed to send password reset confirmation to {user.email}: {e}")
    
    return {
        "message": "Password has been successfully reset",
        "status": "success"
    }

@router.post("/change-password")
def change_password(
    *,
    db: Session = Depends(get_db),
    password_data: schemas.PasswordChangeRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """
    Change password for logged-in user (requires current password)
    """
    # Only allow LOCAL auth users to change passwords
    if current_user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO users cannot change passwords through this system. Contact your administrator."
        )
    
    # Get full user object
    user = crud.user.get(db, id=current_user.id)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password set for this account"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if new password is different from current
    if verify_password(password_data.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password and clear must_change_password flag
    from sqlalchemy import func
    update_data = {
        "hashed_password": get_password_hash(password_data.new_password),
        "password_changed_at": func.now(),
        "must_change_password": False
    }
    
    updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
    
    logger.info(f"Password changed for user: {user.email}")
    
    return {
        "message": "Password has been successfully changed",
        "status": "success"
    }

@router.post("/force-change-password")
def force_change_password(
    *,
    db: Session = Depends(get_db),
    password_data: schemas.ForcePasswordChangeRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """
    Force change password for users who must change password (no current password required)
    """
    # Get full user object
    user = crud.user.get(db, id=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only allow if user must change password
    if not getattr(user, 'must_change_password', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change not required for this user"
        )
    
    # Validate new password
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password and clear must_change_password flag
    from sqlalchemy import func
    update_data = {
        "hashed_password": get_password_hash(password_data.new_password),
        "password_changed_at": func.now(),
        "must_change_password": False
    }
    
    updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
    
    logger.info(f"Forced password change completed for user: {user.email}")
    
    return {
        "message": "Password has been successfully changed",
        "status": "success"
    }

@router.get("/password-policy")
def get_password_policy() -> Any:
    """
    Get password requirements/policy
    """
    return {
        "requirements": {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": False,  # Can be enabled later
        },
        "rules": [
            "Password must be at least 8 characters long",
            "Password must contain at least one uppercase letter",
            "Password must contain at least one lowercase letter", 
            "Password must contain at least one number",
            "Password cannot be the same as your current password"
        ],
        "reset_token_expires": "1 hour",
        "note": "This applies only to local authentication users. SSO users should contact their administrator."
    }