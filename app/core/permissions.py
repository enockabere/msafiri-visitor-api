from typing import List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_roles import UserRole

def has_any_role(user: User, db: Session, required_roles: List[str]) -> bool:
    """Check if user has any of the required roles"""
    # Check primary role first (for backward compatibility)
    if user.role and user.role.value in required_roles:
        return True
    
    # Check additional roles from user_roles table
    user_roles = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.is_active == True
    ).all()
    
    user_role_names = [role.role for role in user_roles]
    return any(role in required_roles for role in user_role_names)

def has_transport_permissions(user: User, db: Session) -> bool:
    """Check if user has permissions for transport management"""
    required_roles = ["super_admin", "mt_admin", "hr_admin", "SUPER_ADMIN", "MT_ADMIN", "HR_ADMIN"]
    return has_any_role(user, db, required_roles)

def has_accommodation_permissions(user: User, db: Session) -> bool:
    """Check if user has permissions for accommodation management"""
    required_roles = ["super_admin", "mt_admin", "hr_admin", "SUPER_ADMIN", "MT_ADMIN", "HR_ADMIN"]
    return has_any_role(user, db, required_roles)

def can_edit_vetting_participants(user: User, db: Session, event_id: int) -> dict:
    """
    Check if user can edit participant roles/statuses during vetting
    Returns dict with: {'can_edit': bool, 'reason': str, 'is_committee': bool, 'is_approver': bool}
    """
    from app.models.vetting_committee import VettingCommittee, VettingStatus, ApprovalStatus
    from datetime import datetime

    # Always allow super admins and event admins
    if user.role and user.role.value in ["super_admin", "event_admin", "SUPER_ADMIN", "EVENT_ADMIN"]:
        return {'can_edit': True, 'reason': 'admin', 'is_committee': False, 'is_approver': False}

    # Get committee for this event
    committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not committee:
        return {'can_edit': False, 'reason': 'no_committee', 'is_committee': False, 'is_approver': False}

    # Check if user is vetting committee member
    is_committee_member = has_any_role(user, db, ["vetting_committee", "VETTING_COMMITTEE"])
    committee_member = any(member.user_id == user.id for member in committee.members)

    # Check if user is approver
    is_approver = has_any_role(user, db, ["vetting_approver", "VETTING_APPROVER"]) or \
                  committee.approver_id == user.id

    # Committee members can edit during OPEN status only
    if is_committee_member and committee_member:
        if committee.status == VettingStatus.OPEN:
            return {'can_edit': True, 'reason': 'committee_open', 'is_committee': True, 'is_approver': False}
        else:
            return {'can_edit': False, 'reason': 'committee_read_only', 'is_committee': True, 'is_approver': False}

    # Approver can edit during PENDING_APPROVAL status only
    if is_approver:
        if committee.status == VettingStatus.PENDING_APPROVAL:
            return {'can_edit': True, 'reason': 'approver_pending', 'is_committee': False, 'is_approver': True}
        else:
            return {'can_edit': False, 'reason': 'approver_read_only', 'is_committee': False, 'is_approver': True}

    return {'can_edit': False, 'reason': 'no_permissions', 'is_committee': False, 'is_approver': False}

def can_view_vetting(user: User, db: Session, event_id: int) -> bool:
    """Check if user can view vetting interface (even after approval)"""
    from app.models.vetting_committee import VettingCommittee
    from datetime import datetime

    # Admins can always view
    if user.role and user.role.value in ["super_admin", "event_admin", "SUPER_ADMIN", "EVENT_ADMIN"]:
        return True

    committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not committee:
        return False

    # Approver can always view (even after approval)
    is_approver = has_any_role(user, db, ["vetting_approver", "VETTING_APPROVER"]) or \
                  committee.approver_id == user.id

    if is_approver:
        return True

    # Committee members can view until deadline
    is_committee_member = has_any_role(user, db, ["vetting_committee", "VETTING_COMMITTEE"])
    committee_member = any(member.user_id == user.id for member in committee.members)

    if is_committee_member and committee_member:
        # Check if deadline passed
        now = datetime.utcnow()
        if now > committee.selection_end_date:
            return False  # Lose access after deadline
        return True

    return False