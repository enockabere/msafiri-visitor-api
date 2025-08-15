# File: app/api/v1/endpoints/profile.py (COMPLETE REWRITE)
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import AuthProvider
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/me", response_model=schemas.UserProfile)
def get_my_profile(
    current_user: schemas.User = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current user's detailed profile"""
    
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
            password_age_days = (datetime.utcnow() - full_user.password_changed_at).days
    
    # Create UserProfile response - FIXED to include all required fields
    return schemas.UserProfile(
        # Core identification
        id=full_user.id,
        email=full_user.email,
        full_name=full_user.full_name or "",
        role=full_user.role,
        status=full_user.status,
        tenant_id=full_user.tenant_id,
        
        # CRITICAL: Core user properties (previously missing)
        is_active=full_user.is_active,
        auth_provider=full_user.auth_provider,
        external_id=full_user.external_id,
        auto_registered=full_user.auto_registered or False,
        
        # Basic profile information
        phone_number=full_user.phone_number,
        department=full_user.department,
        job_title=full_user.job_title,
        
        # Enhanced profile information
        date_of_birth=full_user.date_of_birth,
        nationality=full_user.nationality,
        passport_number=full_user.passport_number,
        passport_issue_date=full_user.passport_issue_date,
        passport_expiry_date=full_user.passport_expiry_date,
        whatsapp_number=full_user.whatsapp_number,
        email_work=full_user.email_work,
        email_personal=full_user.email_personal,
        
        # Timestamps
        last_login=full_user.last_login,
        created_at=full_user.created_at,
        updated_at=full_user.updated_at,
        approved_by=full_user.approved_by,
        approved_at=full_user.approved_at,
        profile_updated_at=full_user.profile_updated_at,
        email_verified_at=full_user.email_verified_at,
        
        # Security indicators
        has_strong_password=has_strong_password,
        password_age_days=password_age_days
    )

@router.put("/me", response_model=schemas.User)
def update_my_profile(
    *,
    db: Session = Depends(get_db),
    profile_update: schemas.UserProfileUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update current user's profile information"""
    
    # Get full user object
    user = crud.user.get(db, id=current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prepare update data - only include fields that were provided
    update_data = profile_update.dict(exclude_unset=True)
    
    # Add metadata
    from sqlalchemy import func
    update_data["profile_updated_at"] = func.now()
    update_data["profile_updated_by"] = current_user.email
    
    # Update the user
    updated_user = crud.user.update(db, db_obj=user, obj_in=update_data)
    
    logger.info(f"Profile updated for user: {user.email}")
    
    return updated_user

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
        "date_of_birth",
        "nationality", 
        "passport_number",
        "passport_issue_date",
        "passport_expiry_date",
        "whatsapp_number",
        "email_work",
        "email_personal"
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
    now = datetime.utcnow()
    
    # Calculate account age
    account_age_days = (now - user.created_at).days if user.created_at else 0
    
    # Get profile completion
    profile_completion = calculate_profile_completion(user)
    
    # Security status
    password_age_days = None
    if user.password_changed_at:
        password_age_days = (now - user.password_changed_at).days
    
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