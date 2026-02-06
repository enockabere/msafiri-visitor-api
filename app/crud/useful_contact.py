from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.useful_contact import UsefulContact
from app.schemas.useful_contact import UsefulContactCreate, UsefulContactUpdate

class CRUDUsefulContact(CRUDBase[UsefulContact, UsefulContactCreate, UsefulContactUpdate]):
    def get_by_tenant(self, db: Session, *, tenant_id: str) -> List[UsefulContact]:
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def create_with_tenant(
        self, db: Session, *, obj_in: UsefulContactCreate, tenant_id: str, created_by: str
    ) -> UsefulContact:
        db_obj = UsefulContact(
            **obj_in.dict(),
            tenant_id=tenant_id,
            created_by=created_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

useful_contact = CRUDUsefulContact(UsefulContact)
