# File: app/crud/invitation.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.crud.base import CRUDBase
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate, InvitationUpdate
from datetime import datetime

class CRUDInvitation(CRUDBase[Invitation, InvitationCreate, InvitationUpdate]):
    
    def get_by_tenant(self, db: Session, *, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Invitation]:
        return (
            db.query(Invitation)
            .filter(
                and_(
                    Invitation.tenant_id == tenant_id,
                    Invitation.expires_at > datetime.utcnow(),
                    Invitation.is_accepted == "false"
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_email_and_tenant(self, db: Session, *, email: str, tenant_id: str) -> Optional[Invitation]:
        return db.query(Invitation).filter(
            and_(
                Invitation.email == email,
                Invitation.tenant_id == tenant_id,
                Invitation.expires_at > datetime.utcnow(),
                Invitation.is_accepted == "false"
            )
        ).first()
    
    def get_by_token(self, db: Session, *, token: str) -> Optional[Invitation]:
        return db.query(Invitation).filter(
            and_(
                Invitation.token == token,
                Invitation.expires_at > datetime.utcnow(),
                Invitation.is_accepted == "false"
            )
        ).first()

invitation = CRUDInvitation(Invitation)