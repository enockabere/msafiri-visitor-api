from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.poa_template import POATemplate
from app.schemas.poa_template import POATemplateCreate, POATemplateUpdate

class CRUDPOATemplate(CRUDBase[POATemplate, POATemplateCreate, POATemplateUpdate]):
    def get_by_vendor(self, db: Session, *, vendor_accommodation_id: int) -> Optional[POATemplate]:
        """Get POA template for a specific vendor hotel"""
        return db.query(POATemplate).filter(
            POATemplate.vendor_accommodation_id == vendor_accommodation_id
        ).first()

    def get_by_tenant(self, db: Session, *, tenant_id: int) -> List[POATemplate]:
        """Get all POA templates for a tenant"""
        return db.query(POATemplate).filter(
            POATemplate.tenant_id == tenant_id,
            POATemplate.is_active == True
        ).all()

    def create_with_tenant(self, db: Session, *, obj_in: POATemplateCreate, tenant_id: int, created_by: int) -> POATemplate:
        """Create POA template with tenant and creator info"""
        db_obj = POATemplate(
            **obj_in.dict(),
            tenant_id=tenant_id,
            created_by=created_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

poa_template = CRUDPOATemplate(POATemplate)
