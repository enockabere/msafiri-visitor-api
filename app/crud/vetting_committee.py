# File: app/crud/vetting_committee.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import secrets

from app.models.vetting_committee import VettingCommittee, VettingCommitteeMember, ParticipantSelection
from app.models.user import User, UserRole as UserRoleEnum, UserStatus, AuthProvider
from app.models.user_roles import UserRole
from app.models.user_tenants import UserTenant, UserTenantRole
from app.models.vetting_role_assignment import VettingRoleAssignment
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.chat import ChatRoom, ChatType, VettingChatRoom, VettingChatMember
from app.schemas.vetting_committee import VettingCommitteeCreate, ParticipantSelectionCreate
from app.core.security import get_password_hash
from datetime import timedelta


def create_vetting_chat_room(
    db: Session,
    committee: VettingCommittee,
    event: Event,
    members: list,
    approvers: list,
    tenant_id: str,
    created_by_id: int
) -> VettingChatRoom:
    """Create a group chat room for vetting committee discussions."""

    # Create the base chat room
    chat_room = ChatRoom(
        chat_type=ChatType.VETTING_CHAT,
        name=f"Vetting: {event.title}",
        event_id=event.id,
        tenant_id=int(tenant_id) if tenant_id.isdigit() else 1,
        is_active=True,
        created_by=created_by_id
    )
    db.add(chat_room)
    db.flush()

    # Calculate deletion date (30 days after event end)
    event_end_date = event.end_date
    scheduled_deletion = None
    if event_end_date:
        if hasattr(event_end_date, 'date'):
            scheduled_deletion = event_end_date + timedelta(days=30)
        else:
            scheduled_deletion = event_end_date + timedelta(days=30)

    # Create vetting chat room extension
    vetting_chat = VettingChatRoom(
        chat_room_id=chat_room.id,
        vetting_committee_id=committee.id,
        event_id=event.id,
        event_end_date=event_end_date if hasattr(event_end_date, 'date') else event_end_date,
        scheduled_deletion_date=scheduled_deletion
    )
    db.add(vetting_chat)
    db.flush()

    # Add committee members to chat
    for member in members:
        chat_member = VettingChatMember(
            vetting_chat_id=vetting_chat.id,
            user_email=member.email,
            user_name=member.full_name,
            role='committee_member',
            can_send_messages=True
        )
        db.add(chat_member)

    # Add approvers to chat
    for approver in approvers:
        chat_member = VettingChatMember(
            vetting_chat_id=vetting_chat.id,
            user_email=approver.email,
            user_name=approver.full_name,
            role='approver',
            can_send_messages=True
        )
        db.add(chat_member)

    return vetting_chat


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
    role_value = "VETTING_COMMITTEE" if role_type == "VETTING_COMMITTEE" else "VETTING_APPROVER"
    existing_role = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role == role_value
    ).first()

    if not existing_role:
        new_role = UserRole(
            user_id=user.id,
            role=role_value
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


def cleanup_vetting_roles_for_event(db: Session, event_id: int) -> int:
    """Remove all vetting roles associated with an event when it's deleted"""
    
    # Get all committees for this event
    committees = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).all()
    
    total_removed = 0
    for committee in committees:
        # Remove vetting roles for this committee
        removed_count = remove_vetting_roles_after_deadline(db, committee.id)
        total_removed += removed_count
        
        # Delete the committee and its members
        db.query(VettingCommitteeMember).filter(
            VettingCommitteeMember.committee_id == committee.id
        ).delete()
        
        db.query(ParticipantSelection).filter(
            ParticipantSelection.committee_id == committee.id
        ).delete()
        
        db.query(VettingRoleAssignment).filter(
            VettingRoleAssignment.committee_id == committee.id
        ).delete()
        
        db.delete(committee)
    
    db.commit()
    return total_removed

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
            role_value = "VETTING_COMMITTEE" if assignment.role_type == "VETTING_COMMITTEE" else "VETTING_APPROVER"
            user_role = db.query(UserRole).filter(
                UserRole.user_id == assignment.user_id,
                UserRole.role == role_value
            ).first()

            if user_role:
                db.delete(user_role)

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
    """Create vetting committee with members and approvers"""
    
    # Create committee
    committee = VettingCommittee(
        event_id=committee_data.event_id,
        selection_start_date=committee_data.selection_start_date,
        selection_end_date=committee_data.selection_end_date,
        approver_email=committee_data.approver_email,  # Legacy field for backward compatibility
        created_by=created_by,
        tenant_id=tenant_id
    )
    
    db.add(committee)
    db.flush()  # Get committee ID
    
    # Handle approvers (new multi-approver system)
    approvers_to_process = []
    if committee_data.approvers:
        # Use new multi-approver system
        approvers_to_process = committee_data.approvers
    elif committee_data.approver_email:
        # Backward compatibility: convert single approver to list
        from app.schemas.vetting_committee import VettingCommitteeApproverCreate
        approvers_to_process = [VettingCommitteeApproverCreate(
            email=committee_data.approver_email,
            full_name="Approver"
        )]
    
    # Create approvers
    from app.models.vetting_committee import VettingCommitteeApprover
    approver_passwords = {}
    for approver_data in approvers_to_process:
        # Create or find approver user
        temp_password = None
        approver = db.query(User).filter(User.email == approver_data.email).first()

        if not approver:
            # Completely new user
            temp_password = secrets.token_urlsafe(12)
            approver = User(
                email=approver_data.email,
                hashed_password=get_password_hash(temp_password),
                full_name=approver_data.full_name,
                role=UserRoleEnum.VETTING_APPROVER,
                status=UserStatus.ACTIVE,
                tenant_id=tenant_id,
                auth_provider=AuthProvider.LOCAL,
                must_change_password=True
            )
            db.add(approver)
            db.flush()
        else:
            # User exists - check if they need local password
            needs_new_password = (
                approver.auth_provider != AuthProvider.LOCAL or 
                not approver.hashed_password or 
                approver.must_change_password
            )
            
            if needs_new_password:
                temp_password = secrets.token_urlsafe(12)
                approver.hashed_password = get_password_hash(temp_password)
                approver.auth_provider = AuthProvider.LOCAL
                approver.must_change_password = True

        # Set legacy approver_id for backward compatibility (use first approver)
        if not committee.approver_id:
            committee.approver_id = approver.id

        # Assign vetting approver role as secondary role
        assign_vetting_role_to_user(db, approver, committee.id, "VETTING_APPROVER", tenant_id)
        
        # Create committee approver record (only if table exists)
        try:
            committee_approver = VettingCommitteeApprover(
                committee_id=committee.id,
                email=approver_data.email,
                full_name=approver_data.full_name,
                user_id=approver.id,
                invitation_token=secrets.token_urlsafe(32)
            )
            db.add(committee_approver)
        except Exception as e:
            # If table doesn't exist, skip creating approver record but continue
            print(f"Warning: Could not create approver record (table may not exist): {e}")
        
        if temp_password:
            approver_passwords[approver_data.email] = temp_password
    
    # Create committee members (existing logic)
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
                role=UserRoleEnum.VETTING_COMMITTEE,
                status=UserStatus.ACTIVE,
                tenant_id=tenant_id,
                auth_provider=AuthProvider.LOCAL,
                must_change_password=True
            )
            db.add(user)
            db.flush()
        else:
            # User exists - store their current role
            had_previous_role = str(user.role.value) if user.role and hasattr(user.role, 'value') else str(user.role) if user.role else None

            # Assign tenant if user doesn't have one
            if not user.tenant_id:
                user.tenant_id = tenant_id

            # Check if they need local password
            needs_new_password = (
                user.auth_provider != AuthProvider.LOCAL or
                not user.hashed_password or
                user.must_change_password
            )

            if needs_new_password:
                member_password = secrets.token_urlsafe(12)
                member_passwords[member_data.email] = member_password
                user.hashed_password = get_password_hash(member_password)
                user.auth_provider = AuthProvider.LOCAL
                user.must_change_password = True

            # Update full name if provided
            user.full_name = member_data.full_name or user.full_name

        # Assign vetting committee role as secondary role
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
    
    # Send invitation emails
    from app.core.email_service import email_service
    import os
    portal_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Get event details for notification
    event = db.query(Event).filter(Event.id == committee_data.event_id).first()
    event_title = event.title if event else "Event"
    
    # Send approver notifications
    for approver_data in approvers_to_process:
        if approver_data.email in approver_passwords:
            try:
                subject = f"Vetting Committee Approver - {event_title}"
                temp_password = approver_passwords[approver_data.email]
                
                credentials_section = f"""
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 24px; border-radius: 12px; margin: 24px 0; border: 2px solid #f59e0b;">
                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 24px; margin-right: 12px;">🔐</span>
                        <span style="font-weight: 700; color: #92400e; font-size: 16px;">Your Login Credentials</span>
                    </div>
                    <div style="background-color: rgba(255,255,255,0.7); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                        <div style="margin-bottom: 12px;">
                            <span style="color: #92400e; font-weight: 600; display: block; margin-bottom: 4px; font-size: 12px; text-transform: uppercase;">Email Address</span>
                            <span style="font-family: 'Courier New', monospace; background-color: #fffbeb; padding: 8px 12px; border-radius: 6px; border: 1px solid #fbbf24; display: inline-block; font-size: 14px;">{approver_data.email}</span>
                        </div>
                        <div>
                            <span style="color: #92400e; font-weight: 600; display: block; margin-bottom: 4px; font-size: 12px; text-transform: uppercase;">Temporary Password</span>
                            <span style="font-family: 'Courier New', monospace; background-color: #fffbeb; padding: 8px 12px; border-radius: 6px; border: 1px solid #fbbf24; display: inline-block; font-size: 14px; letter-spacing: 1px;">{temp_password}</span>
                        </div>
                    </div>
                    <div style="background-color: #fef2f2; padding: 12px; border-radius: 8px; border-left: 4px solid #dc2626;">
                        <span style="color: #991b1b; font-size: 13px;">⚠️ <strong>Important:</strong> Please change your password upon first login for security.</span>
                    </div>
                </div>
                """

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                        <div style="background-color: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                            <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 32px; text-align: center;">
                                <div style="font-size: 32px; margin-bottom: 8px;">🌍</div>
                                <div style="color: white; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">MSF Msafiri</div>
                                <div style="color: rgba(255,255,255,0.9); font-size: 14px; margin-top: 4px;">Event Management Portal</div>
                            </div>
                            <div style="padding: 32px;">
                                <div style="text-align: center; margin-bottom: 24px;">
                                    <span style="background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%); color: white; padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                        ✓ Vetting Committee Approver
                                    </span>
                                </div>
                                <h2 style="color: #1f2937; font-size: 22px; margin: 0 0 8px 0; text-align: center; font-weight: 700;">You've Been Assigned as Approver</h2>
                                <p style="color: #6b7280; text-align: center; margin: 0 0 32px 0; font-size: 15px;">Review and approve participant selections for this event</p>
                                <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 24px; border-radius: 12px; margin-bottom: 24px; border-left: 4px solid #2563eb;">
                                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                                        <span style="font-size: 20px; margin-right: 10px;">📋</span>
                                        <span style="font-weight: 700; color: #1e40af; font-size: 16px;">Event Details</span>
                                    </div>
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <tr>
                                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px; width: 140px;">Event Name</td>
                                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 600;">{event_title}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Selection Period</td>
                                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 600;">{committee_data.selection_start_date.strftime('%B %d, %Y')} - {committee_data.selection_end_date.strftime('%B %d, %Y')}</td>
                                        </tr>
                                    </table>
                                </div>
                                {credentials_section}
                                <div style="text-align: center; margin: 32px 0;">
                                    <a href="{portal_url}/auth/login" style="display: inline-block; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 14px 0 rgba(220, 38, 38, 0.4);">
                                        Login to Portal →
                                    </a>
                                </div>
                            </div>
                            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                                <p style="color: #9ca3af; font-size: 13px; margin: 0 0 8px 0;">This is an automated message from MSF Msafiri</p>
                                <p style="color: #6b7280; font-size: 14px; margin: 0; font-weight: 600;">Médecins Sans Frontières (MSF)</p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                email_service.send_email(
                    to_emails=[approver_data.email],
                    subject=subject,
                    html_content=html_content
                )
            except Exception as e:
                print(f"Failed to send approver notification email to {approver_data.email}: {e}")
    
    # Send member notifications (existing logic)
    for member_data in committee_data.members:
        if member_data.email in member_passwords:
            try:
                member_name = member_data.full_name or member_data.email.split('@')[0]
                subject = f"Vetting Committee Member - {event_title}"
                temp_password = member_passwords[member_data.email]
                
                credentials_section = f"""
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 24px; border-radius: 12px; margin: 24px 0; border: 2px solid #f59e0b;">
                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 24px; margin-right: 12px;">🔐</span>
                        <span style="font-weight: 700; color: #92400e; font-size: 16px;">Your Login Credentials</span>
                    </div>
                    <div style="background-color: rgba(255,255,255,0.7); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                        <div style="margin-bottom: 12px;">
                            <span style="color: #92400e; font-weight: 600; display: block; margin-bottom: 4px; font-size: 12px; text-transform: uppercase;">Email Address</span>
                            <span style="font-family: 'Courier New', monospace; background-color: #fffbeb; padding: 8px 12px; border-radius: 6px; border: 1px solid #fbbf24; display: inline-block; font-size: 14px;">{member_data.email}</span>
                        </div>
                        <div>
                            <span style="color: #92400e; font-weight: 600; display: block; margin-bottom: 4px; font-size: 12px; text-transform: uppercase;">Temporary Password</span>
                            <span style="font-family: 'Courier New', monospace; background-color: #fffbeb; padding: 8px 12px; border-radius: 6px; border: 1px solid #fbbf24; display: inline-block; font-size: 14px; letter-spacing: 1px;">{temp_password}</span>
                        </div>
                    </div>
                    <div style="background-color: #fef2f2; padding: 12px; border-radius: 8px; border-left: 4px solid #dc2626;">
                        <span style="color: #991b1b; font-size: 13px;">⚠️ <strong>Important:</strong> Please change your password upon first login for security.</span>
                    </div>
                </div>
                """

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                        <div style="background-color: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
                            <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 32px; text-align: center;">
                                <div style="font-size: 32px; margin-bottom: 8px;">🌍</div>
                                <div style="color: white; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">MSF Msafiri</div>
                                <div style="color: rgba(255,255,255,0.9); font-size: 14px; margin-top: 4px;">Event Management Portal</div>
                            </div>
                            <div style="padding: 32px;">
                                <div style="text-align: center; margin-bottom: 24px;">
                                    <span style="background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                        ✓ Vetting Committee Member
                                    </span>
                                </div>
                                <h2 style="color: #1f2937; font-size: 22px; margin: 0 0 8px 0; text-align: center; font-weight: 700;">Welcome to the Vetting Committee!</h2>
                                <p style="color: #6b7280; text-align: center; margin: 0 0 8px 0; font-size: 15px;">Hello <strong>{member_name}</strong>,</p>
                                <p style="color: #6b7280; text-align: center; margin: 0 0 32px 0; font-size: 15px;">You've been invited to review and select participants</p>
                                <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); padding: 24px; border-radius: 12px; margin-bottom: 24px; border-left: 4px solid #2563eb;">
                                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                                        <span style="font-size: 20px; margin-right: 10px;">📋</span>
                                        <span style="font-weight: 700; color: #1e40af; font-size: 16px;">Event Details</span>
                                    </div>
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <tr>
                                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px; width: 140px;">Event Name</td>
                                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 600;">{event_title}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Selection Period</td>
                                            <td style="padding: 8px 0; color: #1f2937; font-size: 14px; font-weight: 600;">{committee_data.selection_start_date.strftime('%B %d, %Y')} - {committee_data.selection_end_date.strftime('%B %d, %Y')}</td>
                                        </tr>
                                    </table>
                                </div>
                                {credentials_section}
                                <div style="text-align: center; margin: 32px 0;">
                                    <a href="{portal_url}/auth/login" style="display: inline-block; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 14px 0 rgba(220, 38, 38, 0.4);">
                                        Login to Portal →
                                    </a>
                                </div>
                            </div>
                            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                                <p style="color: #9ca3af; font-size: 13px; margin: 0 0 8px 0;">This is an automated message from MSF Msafiri</p>
                                <p style="color: #6b7280; font-size: 14px; margin: 0; font-weight: 600;">Médecins Sans Frontières (MSF)</p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """

                email_service.send_email(
                    to_emails=[member_data.email],
                    subject=subject,
                    html_content=html_content
                )
            except Exception as e:
                print(f"Failed to send member notification email to {member_data.email}: {e}")

    # Create vetting chat room for committee discussions
    try:
        # Get the creator user for the chat room
        creator = db.query(User).filter(User.email == created_by).first()
        creator_id = creator.id if creator else 1

        # Get all members and approvers for chat
        from app.models.vetting_committee import VettingCommitteeApprover
        committee_members = db.query(VettingCommitteeMember).filter(
            VettingCommitteeMember.committee_id == committee.id
        ).all()
        committee_approvers = db.query(VettingCommitteeApprover).filter(
            VettingCommitteeApprover.committee_id == committee.id
        ).all()

        create_vetting_chat_room(
            db=db,
            committee=committee,
            event=event,
            members=committee_members,
            approvers=committee_approvers,
            tenant_id=tenant_id,
            created_by_id=creator_id
        )
        db.commit()
        print(f"Created vetting chat room for committee {committee.id}")
    except Exception as e:
        print(f"Failed to create vetting chat room: {e}")
        # Don't fail the whole operation if chat creation fails

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
