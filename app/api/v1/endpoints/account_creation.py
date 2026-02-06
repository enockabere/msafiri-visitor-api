from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.db.database import get_db
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.core.email_service import EmailService
import random
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class RequestAccessRequest(BaseModel):
    email: EmailStr

class CreateAccountRequest(BaseModel):
    email: EmailStr
    otp: str
    password: str
    first_name: str
    last_name: str

# Store OTPs temporarily (in production, use Redis)
account_creation_otps = {}

@router.post("/request-access")
async def request_access(request: RequestAccessRequest, db: Session = Depends(get_db)):
    """
    Validate email and check if user can create an account.
    - Reject MSF emails
    - Check if user already exists
    - Check if participant is selected for any event
    - Send OTP if eligible
    """
    email = request.email.lower().strip()
    
    logger.info(f"🔐 Account creation request for email: {email}")
    
    # Check if MSF email
    if '.msf.org' in email:
        logger.warning(f"❌ MSF email attempted account creation: {email}")
        raise HTTPException(status_code=400, detail="MSF users must use Microsoft login")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        logger.warning(f"❌ User already exists: {email}")
        raise HTTPException(
            status_code=400, 
            detail="Account already exists. Please use 'Forgot Password' to reset your password."
        )
    
    # Check if participant exists with status 'selected'
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == email,
        EventParticipant.status == 'selected'
    ).first()
    
    if not participant:
        logger.warning(f"❌ No selected participant found for: {email}")
        raise HTTPException(
            status_code=400,
            detail="You have not been selected to attend any event. Please contact the event organizer."
        )
    
    # Generate 4-digit OTP
    otp = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    
    # Store OTP with expiry (10 minutes)
    account_creation_otps[email] = {
        'otp': otp,
        'expiry': datetime.utcnow() + timedelta(minutes=10),
        'participant_id': participant.id
    }
    
    logger.info(f"✅ Generated account creation OTP for: {email}")
    
    # Send OTP email
    try:
        email_service = EmailService()
        await email_service.send_account_creation_otp_email(
            to_email=email,
            recipient_name=f"{participant.first_name} {participant.last_name}",
            otp_code=otp
        )
        logger.info(f"📧 Account creation OTP email sent to: {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    return {
        "message": "OTP sent to your email. Please check your inbox.",
        "email": email
    }

@router.post("/verify-otp-and-create-account")
async def verify_otp_and_create_account(
    request: CreateAccountRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and create user account
    """
    email = request.email.lower().strip()
    
    logger.info(f"🔐 Account creation attempt for email: {email}")
    
    # Check if OTP exists
    if email not in account_creation_otps:
        logger.warning(f"❌ No OTP found for user: {email}")
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    otp_data = account_creation_otps[email]
    
    # Check if OTP expired
    if datetime.utcnow() > otp_data['expiry']:
        del account_creation_otps[email]
        logger.warning(f"❌ Expired OTP for user: {email}")
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Verify OTP
    if otp_data['otp'] != request.otp:
        logger.warning(f"❌ Invalid OTP for user: {email}")
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Get participant details
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == otp_data['participant_id']
    ).first()
    
    if not participant:
        logger.error(f"❌ Participant not found for: {email}")
        raise HTTPException(status_code=400, detail="Participant not found")
    
    # Create user account
    from app.core.security import get_password_hash
    
    new_user = User(
        email=email,
        first_name=request.first_name,
        last_name=request.last_name,
        hashed_password=get_password_hash(request.password),
        is_active=True,
        role='GUEST',
        tenant_id=participant.tenant_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Clean up OTP
    del account_creation_otps[email]
    
    logger.info(f"✅ Account created successfully for: {email}")
    
    return {
        "message": "Account created successfully! You can now login.",
        "user_id": new_user.id
    }
