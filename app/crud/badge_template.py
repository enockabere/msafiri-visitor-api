from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.badge_template import BadgeTemplate
from app.schemas.badge_template import BadgeTemplateCreate, BadgeTemplateUpdate


class CRUDBadgeTemplate(CRUDBase[BadgeTemplate, BadgeTemplateCreate, BadgeTemplateUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[BadgeTemplate]:
        return db.query(BadgeTemplate).filter(BadgeTemplate.name == name).first()
    
    def get_active_templates(self, db: Session) -> List[BadgeTemplate]:
        return db.query(BadgeTemplate).filter(BadgeTemplate.is_active == True).all()
    
    def get_by_tenant(self, db: Session, *, tenant_id: int, skip: int = 0, limit: int = 100) -> List[BadgeTemplate]:
        return db.query(BadgeTemplate).filter(BadgeTemplate.tenant_id == tenant_id).offset(skip).limit(limit).all()
    
    def get_active_by_tenant(self, db: Session, *, tenant_id: int) -> List[BadgeTemplate]:
        return db.query(BadgeTemplate).filter(
            BadgeTemplate.tenant_id == tenant_id,
            BadgeTemplate.is_active == True
        ).all()


badge_template = CRUDBadgeTemplate(BadgeTemplate)