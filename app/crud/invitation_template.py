from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.invitation_template import InvitationTemplate
from app.schemas.invitation_template import InvitationTemplateCreate, InvitationTemplateUpdate

class CRUDInvitationTemplate(CRUDBase[InvitationTemplate, InvitationTemplateCreate, InvitationTemplateUpdate]):
    def get_active_templates(self, db: Session) -> List[InvitationTemplate]:
        return db.query(InvitationTemplate).filter(InvitationTemplate.is_active == True).all()
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[InvitationTemplate]:
        return db.query(InvitationTemplate).filter(InvitationTemplate.name == name).first()

invitation_template = CRUDInvitationTemplate(InvitationTemplate)