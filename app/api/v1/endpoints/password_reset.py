from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app import crud
from app.core.email_service import email_service
from app.models.user import UserRole
import secrets
import logging
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/request-password-reset")
def request_password_reset(
    *,
    db: Session = Depends(get_db),
    email_data: dict
) -> Any:
    """Request password reset for super admin users only"""
    
    email = email_data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required"
        )
    
    logger.info(f"🔐 Password reset requested for email: {email}")
    
    # Get user by email
    user = crud.user.get_by_email(db, email=email)
    if not user:
        # Don't reveal if user exists or not for security
        logger.info(f"❌ Password reset requested for non-existent user: {email}")
        return {"message": "If the email exists in our system, you will receive a password reset link shortly."}
    
    # Only allow password reset for super admins
    if user.role != UserRole.SUPER_ADMIN:
        logger.warning(f"❌ Password reset attempted for non-super-admin user: {email} (role: {user.role})")
        return {"message": "If the email exists in our system, you will receive a password reset link shortly."}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
    
    # Store reset token in user record
    user.password_reset_token = reset_token
    user.password_reset_expires = reset_expires
    db.commit()
    
    logger.info(f"✅ Generated password reset token for user: {email}")
    
    # Send reset email
    try:
        reset_url = f"{get_frontend_url()}/reset-password?token={reset_token}"
        
        email_service.send_password_reset_email(
            to_email=user.email,
            user_name=user.full_name,
            reset_url=reset_url,
            expires_in_hours=1
        )
        
        logger.info(f"📧 Password reset email sent to: {email}")
        
    except Exception as e:
        logger.error(f"💥 Failed to send password reset email to {email}: {str(e)}")
        # Don't fail the request if email fails, but log the error
    
    return {"message": "If the email exists in our system, you will receive a password reset link shortly."}

@router.post("/reset-password")
def reset_password(
    *,
    db: Session = Depends(get_db),
    reset_data: dict
) -> Any:
    """Reset password using token"""
    
    token = reset_data.get("token", "").strip()
    new_password = reset_data.get("password", "").strip()
    
    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token and new password are required"
        )
    
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    logger.info(f"🔐 Password reset attempt with token: {token[:8]}...")
    
    # Find user by reset token
    user = crud.user.get_by_reset_token(db, token=token)
    if not user:
        logger.warning(f"❌ Invalid password reset token: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        logger.warning(f"❌ Expired password reset token for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Update password
    user.hashed_password = crud.user.get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    
    logger.info(f"✅ Password reset successful for user: {user.email}")
    
    return {"message": "Password has been reset successfully. You can now login with your new password."}

def get_frontend_url() -> str:
    """Get frontend URL for reset links"""
    import os
    return os.getenv("FRONTEND_URL", "http://localhost:3000/portal")