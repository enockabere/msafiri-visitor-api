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
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get current user's consent status"""
    consent = crud.user_consent.get_by_user_id(db, user_id=current_user.id)
    if not consent:
        # Return default consent object if none exists
        return schemas.UserConsent(
            id=0,
            user_id=current_user.id,
            tenant_id=tenant_context,
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
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create or update user consent"""
    existing_consent = crud.user_consent.get_by_user_id(db, user_id=current_user.id)
    
    if existing_consent:
        # Update existing consent
        consent = crud.user_consent.update_consent(
            db, db_obj=existing_consent, obj_in=schemas.UserConsentUpdate(**consent_in.dict())
        )
    else:
        # Create new consent
        consent = crud.user_consent.create_with_user(
            db, obj_in=consent_in, user_id=current_user.id, tenant_id=tenant_context
        )
    
    return consent

@router.get("/check")
def check_consent_status(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Check if user has accepted all required consents"""
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