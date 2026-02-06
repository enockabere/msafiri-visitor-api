"""
Vetting Role Cleanup Service

Cleans up orphaned vetting roles from users when they are not tied to any existing events.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.user_roles import UserRole, RoleType
from app.models.vetting_committee import VettingCommitteeMember
from app.models.event import Event
from datetime import datetime

logger = logging.getLogger(__name__)

def cleanup_orphaned_vetting_roles(db: Session) -> int:
    """
    Remove vetting roles from users who are not tied to any existing events.
    Returns the number of roles cleaned up.
    """
    try:
        logger.info("🧹 Starting cleanup of orphaned vetting roles")
        
        # Get all users with vetting roles
        vetting_roles = db.query(UserRole).filter(
            UserRole.role.in_([RoleType.VETTING_COMMITTEE, RoleType.VETTING_APPROVER])
        ).all()
        
        logger.info(f"🔍 Found {len(vetting_roles)} active vetting roles to check")
        
        cleaned_up_count = 0
        
        for user_role in vetting_roles:
            user_id = user_role.user_id
            role_type = user_role.role
            
            # Check if user is tied to any existing events through vetting committee membership
            has_active_vetting = False
            
            if role_type == RoleType.VETTING_COMMITTEE:
                # Check if user is a member of any vetting committee for existing events
                active_membership = db.execute(text("""
                    SELECT vcm.id 
                    FROM vetting_committee_members vcm
                    JOIN vetting_committees vc ON vcm.committee_id = vc.id
                    JOIN events e ON vc.event_id = e.id
                    WHERE vcm.user_id = :user_id
                    LIMIT 1
                """), {"user_id": user_id}).fetchone()
                
                has_active_vetting = active_membership is not None
                
            elif role_type == RoleType.VETTING_APPROVER:
                # Check if user is an approver for any vetting committee for existing events
                active_approval = db.execute(text("""
                    SELECT vc.id 
                    FROM vetting_committees vc
                    JOIN events e ON vc.event_id = e.id
                    WHERE vc.approver_id = :user_id
                    LIMIT 1
                """), {"user_id": user_id}).fetchone()
                
                has_active_vetting = active_approval is not None
            
            # If user has no active vetting responsibilities, remove the role
            if not has_active_vetting:
                logger.info(f"🗑️ Removing orphaned {role_type.value} role from user {user_id}")

                # Delete the role
                db.delete(user_role)

                cleaned_up_count += 1
        
        db.commit()
        
        logger.info(f"✅ Cleanup completed: {cleaned_up_count} orphaned vetting roles removed")
        return cleaned_up_count
        
    except Exception as e:
        logger.error(f"❌ Error during vetting role cleanup: {str(e)}")
        db.rollback()
        raise e

def cleanup_orphaned_vetting_roles_for_deleted_event(db: Session, event_id: int) -> int:
    """
    Clean up vetting roles specifically when an event is deleted.
    Returns the number of roles cleaned up.
    """
    try:
        logger.info(f"🧹 Cleaning up vetting roles for deleted event {event_id}")
        
        # Get all vetting committee members for this event
        members_to_cleanup = db.execute(text("""
            SELECT DISTINCT vcm.user_id, vcm.email
            FROM vetting_committee_members vcm
            JOIN vetting_committees vc ON vcm.committee_id = vc.id
            WHERE vc.event_id = :event_id AND vcm.user_id IS NOT NULL
        """), {"event_id": event_id}).fetchall()
        
        # Get approvers for this event
        approvers_to_cleanup = db.execute(text("""
            SELECT DISTINCT vc.approver_id, vc.approver_email
            FROM vetting_committees vc
            WHERE vc.event_id = :event_id AND vc.approver_id IS NOT NULL
        """), {"event_id": event_id}).fetchall()
        
        cleaned_up_count = 0
        
        # Check each member if they have other active vetting responsibilities
        for member in members_to_cleanup:
            user_id = member.user_id
            
            # Check if user has other active vetting committee memberships
            other_memberships = db.execute(text("""
                SELECT vcm.id 
                FROM vetting_committee_members vcm
                JOIN vetting_committees vc ON vcm.committee_id = vc.id
                JOIN events e ON vc.event_id = e.id
                WHERE vcm.user_id = :user_id AND vc.event_id != :event_id
                LIMIT 1
            """), {"user_id": user_id, "event_id": event_id}).fetchone()
            
            if not other_memberships:
                # Remove VETTING_COMMITTEE role
                vetting_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role == RoleType.VETTING_COMMITTEE
                ).first()

                if vetting_role:
                    logger.info(f"🗑️ Removing VETTING_COMMITTEE role from user {user_id} (event {event_id} deleted)")
                    db.delete(vetting_role)
                    cleaned_up_count += 1
        
        # Check each approver if they have other active vetting responsibilities
        for approver in approvers_to_cleanup:
            user_id = approver.approver_id
            
            # Check if user has other active vetting approver responsibilities
            other_approvals = db.execute(text("""
                SELECT vc.id 
                FROM vetting_committees vc
                JOIN events e ON vc.event_id = e.id
                WHERE vc.approver_id = :user_id AND vc.event_id != :event_id
                LIMIT 1
            """), {"user_id": user_id, "event_id": event_id}).fetchone()
            
            if not other_approvals:
                # Remove VETTING_APPROVER role
                approver_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role == RoleType.VETTING_APPROVER
                ).first()

                if approver_role:
                    logger.info(f"🗑️ Removing VETTING_APPROVER role from user {user_id} (event {event_id} deleted)")
                    db.delete(approver_role)
                    cleaned_up_count += 1
        
        db.commit()
        
        logger.info(f"✅ Event deletion cleanup completed: {cleaned_up_count} vetting roles removed")
        return cleaned_up_count
        
    except Exception as e:
        logger.error(f"❌ Error during event deletion vetting role cleanup: {str(e)}")
        db.rollback()
        raise e
