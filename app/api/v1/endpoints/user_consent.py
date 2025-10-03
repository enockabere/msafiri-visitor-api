from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db

router = APIRouter()

@router.get("/", response_model=schemas.UserConsent)
def get_user_consent(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get current user's consent status"""
    consent = crud.user_consent.get_by_user_id(db, user_id=current_user.id)
    if not consent:
        # Return default consent object if none exists
        tenant_id = current_user.tenant_id or 'mobile'
        return schemas.UserConsent(
            id=0,
            user_id=current_user.id,
            tenant_id=tenant_id,
            data_protection_accepted=False,
            terms_conditions_accepted=False,
            created_at=current_user.created_at,
        )
    return consent

@router.post("/", response_model=schemas.UserConsent)
def create_or_update_consent(
    *,
    db: Session = Depends(get_db),
    consent_in: schemas.UserConsentCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Create or update user consent"""
    existing_consent = crud.user_consent.get_by_user_id(db, user_id=current_user.id)
    
    # Use user's tenant_id or default to 'mobile' for mobile users
    tenant_id = current_user.tenant_id or 'mobile'
    
    if existing_consent:
        # Update existing consent
        consent = crud.user_consent.update_consent(
            db, db_obj=existing_consent, obj_in=schemas.UserConsentUpdate(**consent_in.dict())
        )
    else:
        # Create new consent
        consent = crud.user_consent.create_with_user(
            db, obj_in=consent_in, user_id=current_user.id, tenant_id=tenant_id
        )
    
    return consent

@router.get("/check")
def check_consent_status(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Check if user has accepted all required consents - No tenant context required for mobile users"""
    consent = crud.user_consent.get_by_user_id(db, user_id=current_user.id)
    
    if not consent:
        return {
            "has_accepted_all": False,
            "data_protection_accepted": False,
            "terms_conditions_accepted": False,
        }
    
    has_accepted_all = consent.data_protection_accepted and consent.terms_conditions_accepted
    
    return {
        "has_accepted_all": has_accepted_all,
        "data_protection_accepted": consent.data_protection_accepted,
        "terms_conditions_accepted": consent.terms_conditions_accepted,
    }

@router.get("/policies")
def get_consent_policies(
    # No authentication required for policy information
) -> Any:
    """Get current consent policies and their details - Public endpoint"""
    return {
        "data_protection_link": "https://www.msf.org/privacy-policy",
        "terms_conditions_link": "https://www.msf.org/terms-and-conditions",
        "data_protection_version": "2.1",
        "terms_conditions_version": "2.1",
        "data_protection_summary": "We collect and process your personal data to provide our services effectively. Your data is protected according to international standards including GDPR and will never be shared with third parties without your explicit consent. We use your information to improve your experience and ensure the security of our services.",
        "terms_conditions_summary": "By using MSF Msafiri, you agree to our terms of service which govern your use of the application. These terms outline your rights, responsibilities, and our commitment to providing you with reliable and secure services. Please review the full document for complete details."
    }