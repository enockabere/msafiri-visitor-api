from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.admin_invitations import AdminInvitation
from app.schemas.admin_invitations import AdminInvitationCreate
import secrets
from datetime import datetime, timedelta

class CRUDAdminInvitation(CRUDBase[AdminInvitation, AdminInvitationCreate, dict]):
    
    def create_invitation(
        self, 
        db: Session, 
        *, 
        email: str, 
        invited_by: str,
        user_existed: bool = False,
        user_id: Optional[int] = None
    ) -> AdminInvitation:
        """Create a new admin invitation with magic link"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Set expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        invitation = AdminInvitation(
            email=email,
            invitation_token=token,
            invited_by=invited_by,
            expires_at=expires_at,
            user_existed=user_existed,
            user_id=user_id
        )
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    
    def get_by_token(self, db: Session, *, token: str) -> Optional[AdminInvitation]:
        """Get invitation by token"""
        return db.query(AdminInvitation).filter(
            AdminInvitation.invitation_token == token,
            AdminInvitation.status == "pending",
            AdminInvitation.expires_at > func.now()
        ).first()
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[AdminInvitation]:
        """Get pending invitation by email"""
        return db.query(AdminInvitation).filter(
            AdminInvitation.email == email,
            AdminInvitation.status == "pending",
            AdminInvitation.expires_at > func.now()
        ).first()
    
    def accept_invitation(self, db: Session, *, invitation: AdminInvitation) -> AdminInvitation:
        """Mark invitation as accepted"""
        invitation.status = "accepted"
        invitation.accepted_at = func.now()
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    
    def get_pending_invitations(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[AdminInvitation]:
        """Get all pending invitations"""
        return db.query(AdminInvitation).filter(
            AdminInvitation.status == "pending",
            AdminInvitation.expires_at > func.now()
        ).offset(skip).limit(limit).all()

admin_invitation = CRUDAdminInvitation(AdminInvitation)