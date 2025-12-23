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


badge_template = CRUDBadgeTemplate(BadgeTemplate)