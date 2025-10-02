from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.emergency_contact import EmergencyContact
from app.schemas.emergency_contact import EmergencyContactCreate, EmergencyContactUpdate

class CRUDEmergencyContact(CRUDBase[EmergencyContact, EmergencyContactCreate, EmergencyContactUpdate]):
    def get_by_user(self, db: Session, *, user_id: int) -> List[EmergencyContact]:
        return db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()
    
    def get_primary_contact(self, db: Session, *, user_id: int) -> Optional[EmergencyContact]:
        return db.query(EmergencyContact).filter(
            EmergencyContact.user_id == user_id,
            EmergencyContact.is_primary == 1
        ).first()
    
    def create_with_user(self, db: Session, *, obj_in: EmergencyContactCreate, user_id: int) -> EmergencyContact:
        obj_in_data = obj_in.dict()
        obj_in_data["user_id"] = user_id
        
        # If this is set as primary, unset other primary contacts
        if obj_in_data.get("is_primary"):
            db.query(EmergencyContact).filter(
                EmergencyContact.user_id == user_id,
                EmergencyContact.is_primary == 1
            ).update({"is_primary": 0})
            obj_in_data["is_primary"] = 1
        else:
            obj_in_data["is_primary"] = 0
            
        db_obj = EmergencyContact(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_with_user_check(self, db: Session, *, db_obj: EmergencyContact, obj_in: EmergencyContactUpdate, user_id: int) -> EmergencyContact:
        # Verify the contact belongs to the user
        if db_obj.user_id != user_id:
            raise ValueError("Emergency contact does not belong to user")
        
        obj_data = obj_in.dict(exclude_unset=True)
        
        # If setting as primary, unset other primary contacts
        if obj_data.get("is_primary"):
            db.query(EmergencyContact).filter(
                EmergencyContact.user_id == user_id,
                EmergencyContact.is_primary == 1,
                EmergencyContact.id != db_obj.id
            ).update({"is_primary": 0})
            obj_data["is_primary"] = 1
        elif "is_primary" in obj_data:
            obj_data["is_primary"] = 0
            
        return super().update(db, db_obj=db_obj, obj_in=obj_data)

emergency_contact = CRUDEmergencyContact(EmergencyContact)