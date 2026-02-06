# File: app/tasks/vetting_cleanup.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.vetting_committee import VettingCommittee, VettingCommitteeMember
from app.models.user import User, UserRole
import logging

logger = logging.getLogger(__name__)

def cleanup_expired_vetting_roles():
    """
    Background task to revoke VETTING_COMMITTEE roles when vetting period ends
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Find all vetting committees where selection period has ended
        expired_committees = db.query(VettingCommittee).filter(
            VettingCommittee.selection_end_date < now
        ).all()
        
        revoked_count = 0
        
        for committee in expired_committees:
            # Get all members of this committee
            members = db.query(VettingCommitteeMember).filter(
                VettingCommitteeMember.committee_id == committee.id
            ).all()
            
            for member in members:
                # Find the user
                user = db.query(User).filter(User.email == member.email).first()
                if user and user.role == UserRole.VETTING_COMMITTEE:
                    # Check if user is member of any other active vetting committees
                    other_active_committees = db.query(VettingCommittee).join(
                        VettingCommitteeMember,
                        VettingCommittee.id == VettingCommitteeMember.committee_id
                    ).filter(
                        VettingCommitteeMember.email == user.email,
                        VettingCommittee.id != committee.id,
                        VettingCommittee.selection_end_date >= now
                    ).first()
                    
                    # Only revoke role if user is not part of any other active committees
                    if not other_active_committees:
                        # Revert to a default role or remove role entirely
                        # For now, we'll set them to a basic user role
                        # You might want to store their original role before making them vetting committee members
                        user.role = UserRole.USER  # or whatever default role you prefer
                        revoked_count += 1
                        logger.info(f"Revoked VETTING_COMMITTEE role from user {user.email}")
        
        if revoked_count > 0:
            db.commit()
            logger.info(f"Successfully revoked VETTING_COMMITTEE role from {revoked_count} users")
        else:
            logger.info("No expired vetting committee roles to revoke")
            
    except Exception as e:
        logger.error(f"Error in cleanup_expired_vetting_roles: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_expired_vetting_roles()
