from sqlalchemy.orm import Session
from typing import Optional
from app.models.privacy_policy import PrivacyPolicy
from app.schemas.privacy_policy import PrivacyPolicyCreate, PrivacyPolicyUpdate

class PrivacyPolicyCRUD:
    def get_active_policy(self, db: Session) -> Optional[PrivacyPolicy]:
        """Get the current active privacy policy"""
        return db.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == True).first()
    
    def get_policy_by_id(self, db: Session, policy_id: int) -> Optional[PrivacyPolicy]:
        """Get privacy policy by ID"""
        return db.query(PrivacyPolicy).filter(PrivacyPolicy.id == policy_id).first()
    
    def create_policy(self, db: Session, policy_data: PrivacyPolicyCreate, created_by: str) -> PrivacyPolicy:
        """Create a new privacy policy"""
        db_policy = PrivacyPolicy(
            **policy_data.dict(),
            created_by=created_by,
            is_active=True
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        return db_policy
    
    def update_policy(self, db: Session, policy: PrivacyPolicy, policy_data: PrivacyPolicyUpdate, updated_by: str) -> PrivacyPolicy:
        """Update an existing privacy policy"""
        update_data = policy_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(policy, field, value)
        
        policy.updated_by = updated_by
        db.commit()
        db.refresh(policy)
        return policy
    
    def deactivate_all_policies(self, db: Session):
        """Deactivate all existing privacy policies"""
        db.query(PrivacyPolicy).update({"is_active": False})
        db.commit()
    
    def delete_policy(self, db: Session, policy: PrivacyPolicy):
        """Delete a privacy policy"""
        db.delete(policy)
        db.commit()

privacy_policy_crud = PrivacyPolicyCRUD()