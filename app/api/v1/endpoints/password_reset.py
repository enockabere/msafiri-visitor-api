from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.db.database import get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.core.email_service import email_service
import secrets
import string
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class PasswordResetTokenRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr
    token: str

# Store reset tokens temporarily (in production, use Redis or database)
reset_tokens = {}

@router.post("/send-reset-token")
async def send_password_reset_token(
    request: PasswordResetTokenRequest,
    db: Session = Depends(get_db)
):
    """Send password reset token to user email"""
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate 6-digit token
        token = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Store token with expiry (10 minutes)
        reset_tokens[request.email] = {
            'token': token,
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        # Send email with token
        try:
            email_service.send_notification_email(
                to_email=request.email,
                user_name=user.full_name or request.email,
                title="Password Reset Token",
                message=f"""
Hello {user.full_name or 'User'},

You requested a password reset for your MSafiri account.

Your reset token is: {token}

This token will expire in 10 minutes.

If you didn't request this reset, please ignore this email.

Best regards,
MSF Kenya Team
                """
            )
            
            logger.info(f"Password reset token sent to {request.email}")
            return {"message": "Reset token sent to your email"}
            
        except Exception as e:
            logger.error(f"Failed to send reset token email: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send reset token")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending reset token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reset-with-token")
async def reset_password_with_token(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Reset password using token"""
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if token exists and is valid
        token_data = reset_tokens.get(request.email)
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        # Check if token matches
        if token_data['token'] != request.token:
            raise HTTPException(status_code=400, detail="Invalid token")
        
        # Check if token is expired
        if datetime.utcnow() > token_data['expires_at']:
            # Clean up expired token
            del reset_tokens[request.email]
            raise HTTPException(status_code=400, detail="Token has expired")
        
        # Generate new random password
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Update user password
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        # Clean up used token
        del reset_tokens[request.email]
        
        # Send new password via email
        try:
            email_service.send_notification_email(
                to_email=request.email,
                user_name=user.full_name or request.email,
                title="Password Reset Successful",
                message=f"""
Hello {user.full_name or 'User'},

Your password has been successfully reset.

Your new password is: {new_password}

Please login with this password and change it to something memorable.

For security reasons, please change your password after logging in.

Best regards,
MSF Kenya Team
                """
            )
            
            logger.info(f"Password reset successful for {request.email}")
            return {"message": "Password reset successful. Check your email for the new password."}
            
        except Exception as e:
            logger.error(f"Failed to send new password email: {str(e)}")
            # Password was changed but email failed
            return {"message": "Password reset successful but failed to send email. Please contact support."}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")