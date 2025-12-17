# File: app/crud/vetting_committee.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import secrets

from app.models.vetting_committee import VettingCommittee, VettingCommitteeMember, ParticipantSelection
from app.models.user import User, UserRole as UserRoleEnum, UserStatus, AuthProvider
from app.models.user_roles import UserRole, RoleType
from app.models.user_tenants import UserTenant, UserTenantRole
from app.models.vetting_role_assignment import VettingRoleAssignment
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.schemas.vetting_committee import VettingCommitteeCreate, ParticipantSelectionCreate
from app.core.security import get_password_hash


def assign_vetting_role_to_user(
    db: Session,
    user: User,
    committee_id: int,
    role_type: str,
    tenant_id: str
) -> None:
    """Assign vetting role as secondary role without replacing primary role"""

    # Store assignment in vetting_role_assignments table
    assignment = VettingRoleAssignment(
        user_id=user.id,
        committee_id=committee_id,
        role_type=role_type,
        is_active=True
    )
    db.add(assignment)

    # Add role via user_roles table (secondary role)
    role_enum = RoleType.VETTING_COMMITTEE if role_type == "VETTING_COMMITTEE" else RoleType.VETTING_APPROVER
    existing_role = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role == role_enum,
        UserRole.is_active == True
    ).first()

    if not existing_role:
        new_role = UserRole(
            user_id=user.id,
            role=role_enum,
            granted_by="vetting_system",
            granted_at=datetime.utcnow(),
            is_active=True
        )
        db.add(new_role)

    # Add tenant association if not exists
    existing_tenant = db.query(UserTenant).filter(
        UserTenant.user_id == user.id,
        UserTenant.tenant_id == tenant_id,
        UserTenant.is_active == True
    ).first()

    if not existing_tenant:
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            role=UserTenantRole.STAFF,
            assigned_by="vetting_system",
            is_active=True
        )
        db.add(user_tenant)


def remove_vetting_roles_after_deadline(db: Session, committee_id: int) -> int:
    """Remove vetting roles from committee members after deadline"""

    # Get all active role assignments for this committee
    assignments = db.query(VettingRoleAssignment).filter(
        VettingRoleAssignment.committee_id == committee_id,
        VettingRoleAssignment.is_active == True
    ).all()

    removed_count = 0
    for assignment in assignments:
        # Check if user has this role in OTHER active committees
        other_assignments = db.query(VettingRoleAssignment).filter(
            VettingRoleAssignment.user_id == assignment.user_id,
            VettingRoleAssignment.role_type == assignment.role_type,
            VettingRoleAssignment.committee_id != committee_id,
            VettingRoleAssignment.is_active == True
        ).count()

        # Only remove role if not used in other committees
        if other_assignments == 0:
            role_enum = RoleType.VETTING_COMMITTEE if assignment.role_type == "VETTING_COMMITTEE" else RoleType.VETTING_APPROVER
            user_role = db.query(UserRole).filter(
                UserRole.user_id == assignment.user_id,
                UserRole.role == role_enum,
                UserRole.is_active == True
            ).first()

            if user_role:
                user_role.is_active = False
                user_role.revoked_at = datetime.utcnow()
                user_role.revoked_by = "vetting_system_deadline"

        # Mark assignment as inactive
        assignment.is_active = False
        assignment.removed_at = datetime.utcnow()
        removed_count += 1

    db.commit()
    return removed_count

def create_vetting_committee(
    db: Session, 
    committee_data: VettingCommitteeCreate, 
    created_by: str,
    tenant_id: str
) -> VettingCommittee:
    """Create vetting committee with members"""
    
    # Create committee
    committee = VettingCommittee(
        event_id=committee_data.event_id,
        selection_start_date=committee_data.selection_start_date,
        selection_end_date=committee_data.selection_end_date,
        approver_email=committee_data.approver_email,
        created_by=created_by,
        tenant_id=tenant_id
    )
    
    db.add(committee)
    db.flush()  # Get committee ID
    
    # Create or find approver user
    temp_password = None
    approver = db.query(User).filter(User.email == committee_data.approver_email).first()

    if not approver:
        # Completely new user
        temp_password = secrets.token_urlsafe(12)
        approver = User(
            email=committee_data.approver_email,
            hashed_password=get_password_hash(temp_password),
            full_name="Approver",
            role=UserRoleEnum.USER,  # Default primary role
            status=UserStatus.ACTIVE,
            tenant_id=tenant_id,
            auth_provider=AuthProvider.LOCAL,
            must_change_password=True
        )
        db.add(approver)
        db.flush()
    else:
        # User exists - check if they need local password
        if approver.auth_provider != AuthProvider.LOCAL or not approver.hashed_password:
            # User doesn't have local password, generate one
            temp_password = secrets.token_urlsafe(12)
            approver.hashed_password = get_password_hash(temp_password)
            approver.auth_provider = AuthProvider.LOCAL
            approver.must_change_password = True

    committee.approver_id = approver.id

    # Assign vetting approver role as secondary role (preserve primary role)
    assign_vetting_role_to_user(db, approver, committee.id, "VETTING_APPROVER", tenant_id)
    
    # Create committee members
    member_passwords = {}
    for member_data in committee_data.members:
        # Check if user exists (globally)
        user = db.query(User).filter(User.email == member_data.email).first()

        # Store original role for tracking
        had_previous_role = None

        if not user:
            # Completely new user
            member_password = secrets.token_urlsafe(12)
            member_passwords[member_data.email] = member_password
            user = User(
                email=member_data.email,
                hashed_password=get_password_hash(member_password),
                full_name=member_data.full_name,
                role=UserRoleEnum.USER,  # Default primary role
                status=UserStatus.ACTIVE,
                tenant_id=tenant_id,
                auth_provider=AuthProvider.LOCAL,
                must_change_password=True
            )
            db.add(user)
            db.flush()
        else:
            # User exists - store their current role
            had_previous_role = str(user.role.value) if user.role else None

            # Check if they need local password
            if user.auth_provider != AuthProvider.LOCAL or not user.hashed_password:
                # User doesn't have local password, generate one
                member_password = secrets.token_urlsafe(12)
                member_passwords[member_data.email] = member_password
                user.hashed_password = get_password_hash(member_password)
                user.auth_provider = AuthProvider.LOCAL
                user.must_change_password = True

            # Update full name if provided
            user.full_name = member_data.full_name or user.full_name

        # Assign vetting committee role as secondary role (preserve primary role)
        assign_vetting_role_to_user(db, user, committee.id, "VETTING_COMMITTEE", tenant_id)

        # Create committee member
        member = VettingCommitteeMember(
            committee_id=committee.id,
            email=member_data.email,
            full_name=member_data.full_name,
            user_id=user.id,
            invitation_token=secrets.token_urlsafe(32),
            had_previous_role=had_previous_role
        )
        db.add(member)
    
    db.commit()
    db.refresh(committee)
    
    # Send invitation emails to all users
    from app.core.email_service import email_service
    import os
    portal_url = os.getenv('PORTAL_URL', 'http://localhost:3000')
    
    # Get event details for notification
    event = db.query(Event).filter(Event.id == committee_data.event_id).first()
    event_title = event.title if event else "Event"
    
    # Send approver notification
    try:
        if temp_password:
            message = f"""You have been invited as an approver for the vetting committee for {event_title}.

Selection Period: {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}

Your login credentials:
Email: {committee_data.approver_email}
Temporary Password: {temp_password}

Please log in and change your password on first login.
Login at: {portal_url}/auth/login"""
        else:
            message = f"""You have been added as an approver for the vetting committee for {event_title}.

Selection Period: {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}

Please log in to start the selection process.
Login at: {portal_url}/auth/login"""
        
        email_service.send_notification_email(
            to_email=committee_data.approver_email,
            user_name=committee_data.approver_email.split('@')[0],
            title=f"Vetting Committee Approver - {event_title}",
            message=message
        )
    except Exception as e:
        print(f"Failed to send approver notification email: {e}")
    
    # Send member notifications to all members
    for member_data in committee_data.members:
        try:
            if member_data.email in member_passwords:
                message = f"""You have been invited as a member of the vetting committee for {event_title}.

Selection Period: {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}

Your login credentials:
Email: {member_data.email}
Temporary Password: {member_passwords[member_data.email]}

Please log in and change your password on first login.
Login at: {portal_url}/auth/login"""
            else:
                message = f"""You have been added as a member of the vetting committee for {event_title}.

Selection Period: {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}

Please log in to start the selection process.
Login at: {portal_url}/auth/login"""
            
            email_service.send_notification_email(
                to_email=member_data.email,
                user_name=member_data.full_name or member_data.email.split('@')[0],
                title=f"Vetting Committee Member - {event_title}",
                message=message
            )
        except Exception as e:
            print(f"Failed to send member notification email to {member_data.email}: {e}")
    
    return committee

def get_committee_by_event(db: Session, event_id: int) -> Optional[VettingCommittee]:
    """Get vetting committee for an event"""
    return db.query(VettingCommittee).filter(VettingCommittee.event_id == event_id).first()

def get_committee_for_user(db: Session, user_email: str) -> List[VettingCommittee]:
    """Get committees where user is a member"""
    return db.query(VettingCommittee).join(VettingCommitteeMember).filter(
        VettingCommitteeMember.email == user_email
    ).all()

def submit_selections(
    db: Session,
    committee_id: int,
    selections: List[ParticipantSelectionCreate],
    submitted_by: str
) -> VettingCommittee:
    """Submit participant selections"""
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise ValueError("Committee not found")
    
    # Delete existing selections
    db.query(ParticipantSelection).filter(ParticipantSelection.committee_id == committee_id).delete()
    
    # Create new selections
    for selection_data in selections:
        selection = ParticipantSelection(
            committee_id=committee_id,
            participant_id=selection_data.participant_id,
            selected=selection_data.selected,
            selection_notes=selection_data.selection_notes,
            selected_by=submitted_by,
            selected_at=datetime.utcnow()
        )
        db.add(selection)
    
    # Update committee status
    committee.status = "submitted_for_approval"
    committee.submitted_at = datetime.utcnow()
    committee.submitted_by = submitted_by
    
    db.commit()
    db.refresh(committee)
    return committee

def approve_selections(
    db: Session,
    committee_id: int,
    approval_status: str,
    approval_notes: Optional[str],
    approved_by: str,
    participant_overrides: Optional[List[ParticipantSelectionCreate]] = None
) -> VettingCommittee:
    """Approve or reject participant selections"""
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise ValueError("Committee not found")
    
    # Handle participant overrides
    if participant_overrides:
        for override in participant_overrides:
            selection = db.query(ParticipantSelection).filter(
                and_(
                    ParticipantSelection.committee_id == committee_id,
                    ParticipantSelection.participant_id == override.participant_id
                )
            ).first()
            
            if selection:
                selection.selected = override.selected
                selection.approver_override = True
                selection.override_notes = override.selection_notes
                selection.override_by = approved_by
                selection.override_at = datetime.utcnow()
    
    # Update committee approval status
    committee.approval_status = approval_status
    committee.approved_at = datetime.utcnow()
    committee.approved_by = approved_by
    committee.approval_notes = approval_notes
    
    # If approved, update participant statuses and send notifications
    if approval_status == "approved":
        selections = db.query(ParticipantSelection).filter(
            ParticipantSelection.committee_id == committee_id
        ).all()
        
        for selection in selections:
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == selection.participant_id
            ).first()
            
            if participant:
                participant.status = "selected" if selection.selected else "not_selected"
        
        db.commit()
        
        # Send notifications to selected participants
        from app.services.vetting_notification_service import send_participant_selection_notifications
        send_participant_selection_notifications(committee_id, db)
    else:
        db.commit()
    
    db.refresh(committee)
    return committee