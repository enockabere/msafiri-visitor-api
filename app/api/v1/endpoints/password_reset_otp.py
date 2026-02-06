from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app import crud
from app.core.email_service import email_service
import secrets
import logging
from datetime import datetime, timedelta, timezone

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/request-password-reset-otp")
def request_password_reset_otp(
    *,
    db: Session = Depends(get_db),
    email_data: dict
) -> Any:
    """Request password reset OTP for non-MSF users"""
    
    email = email_data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required"
        )
    
    # Check if email is MSF email
    if email.endswith("@msf.org"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MSF email users must use Microsoft login. Password reset is not available for MSF accounts."
        )
    
    logger.info(f"🔐 Password reset OTP requested for email: {email}")
    
    # Get user by email
    user = crud.user.get_by_email(db, email=email)
    if not user:
        logger.info(f"❌ Password reset requested for non-existent user: {email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found. Please request access first."
        )
    
    # Generate 6-digit OTP
    otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)  # OTP expires in 10 minutes
    
    # Store OTP in user record
    user.password_reset_token = otp
    user.password_reset_expires = otp_expires
    db.commit()
    
    logger.info(f"✅ Generated password reset OTP for user: {email}")
    
    # Send OTP email
    try:
        email_service.send_password_reset_otp_email(
            to_email=user.email,
            user_name=user.full_name,
            otp=otp,
            expires_in_minutes=10
        )
        
        logger.info(f"📧 Password reset OTP email sent to: {email}")
        
    except Exception as e:
        logger.error(f"💥 Failed to send password reset OTP email to {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please try again later."
        )
    
    return {
        "message": "OTP has been sent to your email address.",
        "email": email
    }

@router.post("/verify-otp-and-reset")
def verify_otp_and_reset(
    *,
    db: Session = Depends(get_db),
    reset_data: dict
) -> Any:
    """Verify OTP and reset password"""
    
    email = reset_data.get("email", "").strip().lower()
    otp = reset_data.get("otp", "").strip()
    new_password = reset_data.get("password", "").strip()
    
    if not email or not otp or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, OTP, and new password are required"
        )
    
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    logger.info(f"🔐 Password reset attempt for email: {email}")
    
    # Find user by email
    user = crud.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify OTP
    if not user.password_reset_token or user.password_reset_token != otp:
        logger.warning(f"❌ Invalid OTP for user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # Check if OTP is expired
    if not user.password_reset_expires or user.password_reset_expires < datetime.now(timezone.utc):
        logger.warning(f"❌ Expired OTP for user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    # Update password
    from app.core.security import get_password_hash
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    
    logger.info(f"✅ Password reset successful for user: {email}")
    
    return {"message": "Password has been reset successfully. You can now login with your new password."}
