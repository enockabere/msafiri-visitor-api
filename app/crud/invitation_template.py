from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.invitation_template import InvitationTemplate
from app.schemas.invitation_template import InvitationTemplateCreate, InvitationTemplateUpdate

class CRUDInvitationTemplate(CRUDBase[InvitationTemplate, InvitationTemplateCreate, InvitationTemplateUpdate]):
    def get_by_tenant(self, db: Session, *, tenant_id: int, skip: int = 0, limit: int = 100) -> List[InvitationTemplate]:
        return db.query(InvitationTemplate).filter(InvitationTemplate.tenant_id == tenant_id).offset(skip).limit(limit).all()
    
    def get_active_templates(self, db: Session, *, tenant_id: int) -> List[InvitationTemplate]:
        return db.query(InvitationTemplate).filter(
            InvitationTemplate.is_active == True,
            InvitationTemplate.tenant_id == tenant_id
        ).all()
    
    def get_by_name(self, db: Session, *, name: str, tenant_id: int) -> Optional[InvitationTemplate]:
        return db.query(InvitationTemplate).filter(
            InvitationTemplate.name == name,
            InvitationTemplate.tenant_id == tenant_id
        ).first()

invitation_template = CRUDInvitationTemplate(InvitationTemplate)