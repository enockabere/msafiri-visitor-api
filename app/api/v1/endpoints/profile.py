# File: app/api/v1/endpoints/profile.py (COMPLETE REWRITE)
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import AuthProvider
from app.core.email_service import email_service
from app.core.config import settings
import logging
import secrets
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/me", response_model=schemas.UserProfile)
def get_my_profile(
    current_user: schemas.User = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current user's detailed profile"""
    
    try:
        # Get full user object with all profile fields
        full_user = crud.user.get(db, id=current_user.id)
        if not full_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Calculate security indicators
        has_strong_password = False
        password_age_days = None
        
        if full_user.auth_provider == AuthProvider.LOCAL and full_user.hashed_password:
            has_strong_password = True
            if full_user.password_changed_at:
                now_tz = datetime.now(timezone.utc)
                if full_user.password_changed_at.tzinfo is None:
                    password_changed_tz = full_user.password_changed_at.replace(tzinfo=timezone.utc)
                else:
                    password_changed_tz = full_user.password_changed_at
                password_age_days = (now_tz - password_changed_tz).days
        
        # Create UserProfile response with safe defaults
        return schemas.UserProfile(
            # Core identification
            id=full_user.id,
            email=full_user.email,
            full_name=full_user.full_name or "",
            role=full_user.role,
            status=full_user.status,
            tenant_id=full_user.tenant_id,
            
            # Core user properties with safe defaults
            is_active=getattr(full_user, 'is_active', True),
            auth_provider=getattr(full_user, 'auth_provider', AuthProvider.LOCAL),
            external_id=getattr(full_user, 'external_id', None),
            auto_registered=getattr(full_user, 'auto_registered', False),
            
            # Basic profile information
            phone_number=getattr(full_user, 'phone_number', None),
            department=getattr(full_user, 'department', None),
            job_title=getattr(full_user, 'job_title', None),
            
            # Enhanced profile information
            gender=getattr(full_user, 'gender', None),
            nationality=getattr(full_user, 'nationality', None),
            passport_number=getattr(full_user, 'passport_number', None),
            passport_issue_date=getattr(full_user, 'passport_issue_date', None),
            passport_expiry_date=getattr(full_user, 'passport_expiry_date', None),
            whatsapp_number=getattr(full_user, 'whatsapp_number', None),
            email_work=getattr(full_user, 'email_work', None),
            
            # Timestamps
            last_login=getattr(full_user, 'last_login', None),
            created_at=full_user.created_at,
            updated_at=getattr(full_user, 'updated_at', None),
            approved_by=getattr(full_user, 'approved_by', None),
            approved_at=getattr(full_user, 'approved_at', None),
            profile_updated_at=getattr(full_user, 'profile_updated_at', None),
            email_verified_at=getattr(full_user, 'email_verified_at', None),
            
            # Security indicators
            has_strong_password=has_strong_password,
            password_age_days=password_age_days
        )
    except Exception as e:
        logger.error(f"Error getting user profile for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )

@router.put("/me", response_model=schemas.User)
def update_my_profile(
    *,
    db: Session = Depends(get_db),
    profile_update: schemas.UserProfileUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update current user's profile information"""
    
    try:
        # Get full user object
        user = crud.user.get(db, id=current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare update data - only include fields that were provided
        update_data = profile_update.dict(exclude_unset=True)
        logger.info(f"Profile update data: {update_data}")
        
        # Handle email change separately - require verification
        if "email" in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email changes require verification. Use /profile/request-email-change endpoint."
            )
        
        # Add metadata using Python datetime
        update_data["profile_updated_at"] = datetime.now(timezone.utc)
        update_data["profile_updated_by"] = current_user.email
        
        # Update the user record directly (this updates the users table)
        updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
        
        logger.info(f"Profile updated for user: {user.email}")
        
        return updated_user
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Profile update failed: {str(e)}"
        )

@router.get("/editable-fields", response_model=schemas.EditableFieldsResponse)
def get_editable_fields(
    current_user: schemas.User = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get list of fields that can be edited by current user"""
    
    # Get full user for profile completion calculation
    full_user = crud.user.get(db, id=current_user.id)
    if not full_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Basic fields all users can edit
    basic_fields = [
        "full_name",
        "phone_number", 
        "department",
        "job_title"
    ]
    
    # Enhanced fields
    enhanced_fields = [
        "gender",
        "nationality", 
        "passport_number",
        "passport_issue_date",
        "passport_expiry_date",
        "whatsapp_number",
        "email_work"
    ]
    
    readonly_fields = ["email", "role", "tenant_id", "auth_provider"]
    
    can_change_password = current_user.auth_provider == AuthProvider.LOCAL
    
    profile_completion = calculate_profile_completion(full_user)
    
    return schemas.EditableFieldsResponse(
        basic_fields=basic_fields,
        enhanced_fields=enhanced_fields,
        readonly_fields=readonly_fields,
        can_change_password=can_change_password,
        profile_completion=profile_completion
    )

@router.get("/stats", response_model=schemas.ProfileStatsResponse)
def get_profile_stats(
    current_user: schemas.User = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get profile statistics and insights"""
    
    user = crud.user.get(db, id=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Calculate various stats
    now = datetime.now(timezone.utc)
    
    # Calculate account age - handle timezone awareness
    account_age_days = 0
    if user.created_at:
        if user.created_at.tzinfo is None:
            created_at_tz = user.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_tz = user.created_at
        account_age_days = (now - created_at_tz).days
    
    # Get profile completion
    profile_completion = calculate_profile_completion(user)
    
    # Security status
    password_age_days = None
    if user.password_changed_at:
        if user.password_changed_at.tzinfo is None:
            password_changed_tz = user.password_changed_at.replace(tzinfo=timezone.utc)
        else:
            password_changed_tz = user.password_changed_at
        password_age_days = (now - password_changed_tz).days
    
    security_status = schemas.SecurityStatus(
        auth_method=user.auth_provider.value,
        has_password=user.hashed_password is not None,
        password_age_days=password_age_days,
        email_verified=user.email_verified_at is not None
    )
    
    # Activity info
    activity = schemas.ActivityInfo(
        profile_last_updated=user.profile_updated_at.isoformat() if user.profile_updated_at else None,
        password_last_changed=user.password_changed_at.isoformat() if user.password_changed_at else None
    )
    
    return schemas.ProfileStatsResponse(
        account_age_days=account_age_days,
        last_login=user.last_login.isoformat() if user.last_login else None,
        profile_completion=profile_completion,
        security_status=security_status,
        activity=activity
    )

def calculate_profile_completion(user) -> schemas.ProfileCompletion:
    """Calculate how complete the user's profile is"""
    completed_fields = 0
    total_basic_fields = 4
    missing_fields = []
    
    # Check basic fields
    basic_field_checks = [
        ("full_name", user.full_name),
        ("phone_number", user.phone_number),
        ("department", user.department),
        ("job_title", user.job_title)
    ]
    
    for field_name, field_value in basic_field_checks:
        if field_value and field_value.strip():
            completed_fields += 1
        else:
            missing_fields.append(field_name)
    
    # Calculate completion percentage
    completion_percentage = int((completed_fields / total_basic_fields) * 100)
    
    return schemas.ProfileCompletion(
        percentage=completion_percentage,
        completed_fields=completed_fields,
        total_basic_fields=total_basic_fields,
        missing_fields=missing_fields
    )

class EmailChangeRequest(BaseModel):
    new_email: EmailStr

@router.post("/request-email-change")
def request_email_change(
    *,
    db: Session = Depends(get_db),
    request: EmailChangeRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Request email change with verification"""
    
    # Check if new email is different
    if request.new_email == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email must be different from current email"
        )
    
    # Check if email is already taken
    existing_user = crud.user.get_by_email(db, email=request.new_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use by another account"
        )
    
    # Generate verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Store pending email change
    user = crud.user.get(db, id=current_user.id)
    update_data = {
        "email_verification_token": token,
        "email_verification_expires": expires_at,
        "email_personal": request.new_email  # Store new email temporarily
    }
    crud.user.update(db, db_obj=user, obj_in=update_data)
    
    # Send verification email
    background_tasks.add_task(
        send_email_change_verification,
        request.new_email,
        token,
        current_user.full_name or current_user.email
    )
    
    return {
        "message": "Email verification sent to new address",
        "new_email": request.new_email
    }

class EmailChangeConfirm(BaseModel):
    token: str

@router.post("/confirm-email-change")
def confirm_email_change(
    *,
    db: Session = Depends(get_db),
    request: EmailChangeConfirm
) -> Any:
    """Confirm email change with token (no authentication required)"""
    
    # Find user by verification token
    user = db.query(crud.user.model).filter(
        crud.user.model.email_verification_token == request.token
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Verify token expiry
    now = datetime.now(timezone.utc)
    expires_at = user.email_verification_expires
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if (not user.email_verification_expires or
        expires_at < now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    
    # Get new email from temporary storage
    new_email = user.email_personal
    if not new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending email change found"
        )
    
    # Update email and clear verification data
    update_data = {
        "email": new_email,
        "email_verification_token": None,
        "email_verification_expires": None,
        "email_verified_at": datetime.now(timezone.utc),
        "email_personal": None,  # Clear temporary storage
        "profile_updated_at": datetime.now(timezone.utc)
    }
    
    updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
    
    return {
        "message": "Email successfully changed",
        "new_email": new_email
    }

def send_email_change_verification(new_email: str, token: str, user_name: str):
    """Send email change verification email"""
    try:
        verify_url = f"{settings.frontend_url}/verify-email-change?token={token}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #dc3545;">Verify Email Change</h1>
            
            <p>Hello {user_name},</p>
            
            <p>You have requested to change your email address to <strong>{new_email}</strong>.</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0;"><strong>Important:</strong></p>
                <p style="margin: 5px 0 0 0;">Click the button below to confirm this email change. This link will expire in 24 hours.</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" 
                   style="background: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Verify Email Change
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                If you didn't request this change, please ignore this email.
            </p>
            
            <p style="color: #666; font-size: 12px;">
                Best regards,<br>
                Msafiri Team
            </p>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_emails=[new_email],
            subject="Verify Your Email Change - Msafiri",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Failed to send email change verification to {new_email}: {e}")
