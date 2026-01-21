from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.models.privacy_policy import PrivacyPolicy
from app.crud.privacy_policy import privacy_policy_crud
from app.schemas.privacy_policy import PrivacyPolicyCreate, PrivacyPolicyUpdate, PrivacyPolicyResponse
from app.core.security import require_super_admin

router = APIRouter()

@router.get("/", response_model=Optional[PrivacyPolicyResponse])
def get_current_privacy_policy(
    db: Session = Depends(get_db)
):
    """Get the current active privacy policy"""
    policy = privacy_policy_crud.get_active_policy(db)
    return policy

@router.post("/", response_model=PrivacyPolicyResponse)
def create_privacy_policy(
    policy_data: PrivacyPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new privacy policy (Super Admin only)"""
    require_super_admin(current_user)
    
    # Deactivate existing policies
    privacy_policy_crud.deactivate_all_policies(db)
    
    # Create new policy
    policy = privacy_policy_crud.create_policy(db, policy_data, current_user.email)
    return policy

@router.put("/{policy_id}", response_model=PrivacyPolicyResponse)
def update_privacy_policy(
    policy_id: int,
    policy_data: PrivacyPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing privacy policy (Super Admin only)"""
    require_super_admin(current_user)
    
    policy = privacy_policy_crud.get_policy_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Privacy policy not found"
        )
    
    updated_policy = privacy_policy_crud.update_policy(db, policy, policy_data, current_user.email)
    return updated_policy

@router.delete("/{policy_id}")
def delete_privacy_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a privacy policy (Super Admin only)"""
    require_super_admin(current_user)
    
    policy = privacy_policy_crud.get_policy_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Privacy policy not found"
        )
    
    privacy_policy_crud.delete_policy(db, policy)
    return {"message": "Privacy policy deleted successfully"}