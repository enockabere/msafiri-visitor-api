from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.user_consent import UserConsent
from app.schemas.user_consent import UserConsentCreate, UserConsentUpdate

class CRUDUserConsent(CRUDBase[UserConsent, UserConsentCreate, UserConsentUpdate]):
    def get_by_user_id(self, db: Session, *, user_id: int) -> Optional[UserConsent]:
        return db.query(UserConsent).filter(UserConsent.user_id == user_id).first()
    
    def create_with_user(
        self, db: Session, *, obj_in: UserConsentCreate, user_id: int, tenant_id: str
    ) -> UserConsent:
        now = datetime.utcnow()
        
        db_obj = UserConsent(
            user_id=user_id,
            tenant_id=tenant_id,
            created_at=now,
            **obj_in.dict()
        )
        
        # Set acceptance timestamps
        if obj_in.data_protection_accepted:
            db_obj.data_protection_accepted_at = now
        if obj_in.terms_conditions_accepted:
            db_obj.terms_conditions_accepted_at = now
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_consent(
        self, db: Session, *, db_obj: UserConsent, obj_in: UserConsentUpdate
    ) -> UserConsent:
        update_data = obj_in.dict(exclude_unset=True)
        now = datetime.utcnow()
        
        # Update timestamps when consent is given
        if "data_protection_accepted" in update_data and update_data["data_protection_accepted"]:
            update_data["data_protection_accepted_at"] = now
        if "terms_conditions_accepted" in update_data and update_data["terms_conditions_accepted"]:
            update_data["terms_conditions_accepted_at"] = now
            
        return super().update(db, db_obj=db_obj, obj_in=update_data)

user_consent = CRUDUserConsent(UserConsent)
