# File: app/api/v1/endpoints/vetting_committee.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import csv
import io

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole, UserStatus, AuthProvider
from app.models.event_participant import EventParticipant
from app.schemas.vetting_committee import (
    VettingCommitteeCreate, VettingCommitteeResponse,
    VettingSubmissionRequest, ApprovalDecisionRequest,
    ParticipantSelectionResponse
)
from app.crud import vetting_committee as crud_vetting
from app.models.vetting_committee import VettingCommittee, ParticipantSelection, VettingStatus, VettingCommitteeMember

router = APIRouter()

@router.post("/", response_model=VettingCommitteeResponse)
def create_vetting_committee(
    committee_data: VettingCommitteeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create vetting committee for an event (All authenticated users)"""
    
    # Allow all authenticated users to create vetting committees
    # No role restriction needed
    
    try:
        # Check if committee already exists for this event
        existing = crud_vetting.get_committee_by_event(db, committee_data.event_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vetting committee already exists for this event"
            )
        
        committee = crud_vetting.create_vetting_committee(
            db=db,
            committee_data=committee_data,
            created_by=current_user.email,
            tenant_id=current_user.tenant_id or "default"
        )
        
        return committee
    except Exception as e:
        print(f"ERROR creating vetting committee: {str(e)}")
        print(f"ERROR type: {type(e)}")
        print(f"Current user: {current_user.email if current_user else 'None'}")
        print(f"Current user tenant_id: {current_user.tenant_id if current_user else 'None'}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vetting committee: {str(e)}"
        )

@router.get("/event/{event_id}", response_model=VettingCommitteeResponse)
def get_event_vetting_committee(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get vetting committee for an event"""
    
    committee = crud_vetting.get_committee_by_event(db, event_id)
    if not committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )
    
    # Check permissions - allow SUPER_ADMIN and EVENT_ADMIN full access
    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
        return committee
    elif current_user.role == UserRole.VETTING_COMMITTEE:
        # Check if user is member of this committee
        is_member = any(member.email == current_user.email for member in committee.members)
        if not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return committee
    elif current_user.role == UserRole.VETTING_APPROVER:
        # Check if user is approver for this committee
        if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return committee
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

@router.get("/my-committees", response_model=List[VettingCommitteeResponse])
def get_my_committees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get committees where current user is a member or approver"""
    
    if current_user.role == UserRole.VETTING_COMMITTEE:
        committees = crud_vetting.get_committee_for_user(db, current_user.email)
    elif current_user.role == UserRole.VETTING_APPROVER:
        committees = db.query(VettingCommittee).filter(
            VettingCommittee.approver_email == current_user.email
        ).all()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return committees

@router.get("/my-vetting-events")
def get_my_vetting_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get events where current user has vetting roles with event details"""
    
    from app.models.event import Event
    from sqlalchemy import or_
    
    # Get committees where user is member or approver
    committees = []
    
    # Check by role first
    if current_user.role == UserRole.VETTING_COMMITTEE:
        committees.extend(crud_vetting.get_committee_for_user(db, current_user.email))
    elif current_user.role == UserRole.VETTING_APPROVER:
        committees.extend(db.query(VettingCommittee).filter(
            VettingCommittee.approver_email == current_user.email
        ).all())
    
    # Also check by database relationships (for users who might be members/approvers without explicit roles)
    # Check if user is a committee member
    member_committees = db.query(VettingCommittee).join(
        VettingCommitteeMember, VettingCommittee.id == VettingCommitteeMember.committee_id
    ).filter(
        VettingCommitteeMember.email == current_user.email
    ).all()
    committees.extend(member_committees)
    
    # Check if user is an approver by email or user_id
    approver_committees = db.query(VettingCommittee).filter(
        or_(
            VettingCommittee.approver_email == current_user.email,
            VettingCommittee.approver_id == current_user.id
        )
    ).all()
    committees.extend(approver_committees)
    
    # Remove duplicates
    unique_committees = {}
    for committee in committees:
        unique_committees[committee.id] = committee
    committees = list(unique_committees.values())
    
    # Get event details for each committee
    vetting_events = []
    for committee in committees:
        event = db.query(Event).filter(Event.id == committee.event_id).first()
        if event:
            # Get tenant information
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first() if event.tenant_id else None
            
            # Determine user's role in this committee
            role = "unknown"
            if current_user.role == UserRole.VETTING_COMMITTEE or any(
                member.email == current_user.email for member in committee.members
            ):
                role = "committee_member"
            elif (current_user.role == UserRole.VETTING_APPROVER or 
                  committee.approver_email == current_user.email or 
                  committee.approver_id == current_user.id):
                role = "approver"
            
            vetting_events.append({
                "event_id": event.id,
                "event_title": event.title,
                "event_start_date": event.start_date,
                "event_end_date": event.end_date,
                "committee_id": committee.id,
                "committee_status": committee.status.value,
                "role": role,
                "selection_start_date": committee.selection_start_date,
                "selection_end_date": committee.selection_end_date,
                "tenant_id": tenant.id if tenant else event.tenant_id,
                "tenant_name": tenant.name if tenant else "Unknown Tenant",
                "tenant_slug": tenant.slug if tenant else event.tenant_id
            })
    
    return {"vetting_events": vetting_events}

@router.get("/{committee_id}/participants")
def get_committee_participants(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get participants for vetting committee selection"""
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    # Check permissions based on committee status
    if committee.status == VettingStatus.OPEN:
        # Only committee members can view when open
        if current_user.role == UserRole.VETTING_COMMITTEE:
            is_member = any(member.email == current_user.email for member in committee.members)
            if not is_member:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    elif committee.status == VettingStatus.PENDING_APPROVAL:
        # Committee members (read-only) and approvers can view
        if current_user.role == UserRole.VETTING_COMMITTEE:
            is_member = any(member.email == current_user.email for member in committee.members)
            if not is_member:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        elif current_user.role == UserRole.VETTING_APPROVER:
            if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    elif committee.status == VettingStatus.APPROVED:
        # Read-only for all authorized users
        if current_user.role == UserRole.VETTING_COMMITTEE:
            is_member = any(member.email == current_user.email for member in committee.members)
            if not is_member:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        elif current_user.role == UserRole.VETTING_APPROVER:
            if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        elif current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Get event participants
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == committee.event_id
    ).all()
    
    # Get existing selections
    selections = db.query(ParticipantSelection).filter(
        ParticipantSelection.committee_id == committee_id
    ).all()
    
    selection_map = {s.participant_id: s for s in selections}
    
    result = []
    for participant in participants:
        selection = selection_map.get(participant.id)
        result.append({
            "participant": participant,
            "selection": selection
        })
    
    # Add read-only flag based on status and user role
    read_only = False
    if committee.status == VettingStatus.PENDING_APPROVAL:
        if current_user.role == UserRole.VETTING_COMMITTEE:
            read_only = True
    elif committee.status == VettingStatus.APPROVED:
        read_only = True
    
    return {
        "participants": result,
        "read_only": read_only,
        "status": committee.status.value
    }

@router.post("/{committee_id}/selections", response_model=dict)
def update_participant_selections(
    committee_id: int,
    submission: VettingSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update participant selections (Committee members only when status is open)"""
    
    if current_user.role != UserRole.VETTING_COMMITTEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vetting committee members can update selections"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update selections when committee status is open"
        )
    
    # Check if user is member of this committee
    is_member = any(member.email == current_user.email for member in committee.members)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Update selections using existing CRUD function
    crud_vetting.submit_selections(
        db=db,
        committee_id=committee_id,
        selections=submission.selections,
        submitted_by=current_user.email
    )
    
    return {"message": "Selections updated successfully"}

@router.post("/{committee_id}/edit-selections", response_model=dict)
def edit_participant_selections(
    committee_id: int,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edit participant selections (Approvers only when status is pending approval)"""
    
    if current_user.role != UserRole.VETTING_APPROVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approvers can edit selections"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit selections when committee status is pending approval"
        )
    
    # Check if user is approver for this committee
    if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Update selections using existing CRUD function
    crud_vetting.approve_selections(
        db=db,
        committee_id=committee_id,
        approval_status=decision.approval_status.value,
        approval_notes=decision.approval_notes,
        approved_by=current_user.email,
        participant_overrides=decision.participant_overrides
    )
    
    return {"message": "Selections updated successfully"}

@router.put("/{committee_id}", response_model=VettingCommitteeResponse)
def update_vetting_committee(
    committee_id: int,
    committee_data: VettingCommitteeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update vetting committee (Admin only, only if pending)"""
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update vetting committees"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found"
        )
    
    if committee.status != VettingStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update committees in open status"
        )
    
    # Update committee fields
    committee.selection_start_date = committee_data.selection_start_date
    committee.selection_end_date = committee_data.selection_end_date
    committee.approver_email = committee_data.approver_email
    
    # Update approver role
    approver = db.query(User).filter(User.email == committee_data.approver_email).first()
    if approver:
        from sqlalchemy import text
        db.execute(text("UPDATE users SET role = 'VETTING_APPROVER' WHERE id = :user_id"), {"user_id": approver.id})
        approver.tenant_id = current_user.tenant_id
    
    # Delete existing members
    db.query(VettingCommitteeMember).filter(VettingCommitteeMember.committee_id == committee_id).delete()
    
    # Add new members
    import secrets
    from app.core.security import get_password_hash
    from app.core.email_service import email_service
    import os
    from app.models.event import Event
    
    portal_url = os.getenv('PORTAL_URL', 'http://localhost:3000')
    event = db.query(Event).filter(Event.id == committee.event_id).first()
    event_title = event.title if event else "Event"
    member_passwords = {}
    
    for member_data in committee_data.members:
        user = db.query(User).filter(User.email == member_data.email).first()
        if not user:
            temp_password = secrets.token_urlsafe(12)
            member_passwords[member_data.email] = temp_password
            user = User(
                email=member_data.email,
                hashed_password=get_password_hash(temp_password),
                full_name=member_data.full_name,
                role=UserRole.VETTING_COMMITTEE,
                status=UserStatus.ACTIVE,
                tenant_id=current_user.tenant_id,
                auth_provider=AuthProvider.LOCAL,
                must_change_password=True
            )
            db.add(user)
            db.flush()
        
        member = VettingCommitteeMember(
            committee_id=committee.id,
            email=member_data.email,
            full_name=member_data.full_name,
            user_id=user.id,
            invitation_token=secrets.token_urlsafe(32)
        )
        db.add(member)
    
    db.commit()
    db.refresh(committee)
    
    # Send emails to new members with credentials
    for member_data in committee_data.members:
        if member_data.email in member_passwords:
            try:
                # Create well-structured email content
                subject = f"Vetting Committee Approver - {event_title}"
                
                # Create HTML email content
                html_message = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{subject}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                        .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .header {{ text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 20px; border-radius: 8px; }}
                        .logo {{ color: white; font-size: 24px; font-weight: bold; }}
                        .title {{ color: #1f2937; font-size: 20px; margin: 20px 0; text-align: center; }}
                        .section {{ margin: 20px 0; padding: 15px; background-color: #f9fafb; border-radius: 8px; border-left: 4px solid #dc2626; }}
                        .section-title {{ font-weight: bold; color: #374151; margin-bottom: 10px; }}
                        .credentials {{ background-color: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #f59e0b; }}
                        .credential-item {{ margin: 8px 0; font-family: monospace; font-size: 14px; }}
                        .credential-label {{ font-weight: bold; color: #92400e; display: inline-block; width: 120px; }}
                        .credential-value {{ background-color: #fffbeb; padding: 4px 8px; border-radius: 4px; border: 1px solid #fbbf24; }}
                        .button {{ display: inline-block; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
                        .warning {{ background-color: #fef2f2; padding: 15px; border-radius: 8px; border: 1px solid #fecaca; margin: 20px 0; }}
                        .warning-text {{ color: #991b1b; font-size: 14px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="logo">🌍 MSF Msafiri</div>
                        </div>
                        
                        <h2 class="title">Vetting Committee Approver Invitation</h2>
                        
                        <div class="section">
                            <div class="section-title">Event Information</div>
                            <p><strong>Event:</strong> {event_title}</p>
                            <p><strong>Selection Period:</strong> {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}</p>
                        </div>
                        
                        <div class="section">
                            <div class="section-title">Your Role</div>
                            <p>You have been invited as an <strong>approver</strong> for the vetting committee for this event. You will review and approve participant selections made by the committee members.</p>
                        </div>
                        
                        <div class="credentials">
                            <div class="section-title" style="color: #92400e; margin-bottom: 15px;">🔐 Login Credentials</div>
                            <div class="credential-item">
                                <span class="credential-label">Email:</span>
                                <span class="credential-value">{member_data.email}</span>
                            </div>
                            <div class="credential-item">
                                <span class="credential-label">Password:</span>
                                <span class="credential-value">{member_passwords[member_data.email]}</span>
                            </div>
                        </div>
                        
                        <div class="warning">
                            <div class="warning-text">
                                <strong>⚠️ Important:</strong> Please log in and change your password on first login for security.
                            </div>
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="{portal_url}/auth/login" class="button" style="color: white;">Login to Portal</a>
                        </div>
                        
                        <div class="footer">
                            <p>This is an automated message from MSF Msafiri Admin Portal</p>
                            <p>Médecins Sans Frontières (MSF)</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Create plain text version
                text_message = f"""
{subject}
{'=' * len(subject)}

EVENT INFORMATION
-----------------
Event: {event_title}
Selection Period: {committee_data.selection_start_date.strftime('%Y-%m-%d')} to {committee_data.selection_end_date.strftime('%Y-%m-%d')}

YOUR ROLE
---------
You have been invited as an approver for the vetting committee for this event. You will review and approve participant selections made by the committee members.

LOGIN CREDENTIALS
-----------------
Email: {member_data.email}
Temporary Password: {member_passwords[member_data.email]}

IMPORTANT: Please log in and change your password on first login for security.

Login at: {portal_url}/auth/login

---
This is an automated message from MSF Msafiri Admin Portal
Médecins Sans Frontières (MSF)
                """
                
                # Send the email using the email service
                email_service.send_email(
                    to_emails=[member_data.email],
                    subject=subject,
                    html_content=html_message,
                    text_content=text_message
                )
            except Exception as e:
                print(f"Failed to send member notification email to {member_data.email}: {e}")
    
    return committee

@router.post("/{committee_id}/submit-for-approval", response_model=VettingCommitteeResponse)
def submit_for_approval(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit committee selections for approval (Committee members only)"""
    
    if current_user.role != UserRole.VETTING_COMMITTEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only committee members can submit for approval"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit committees in open status"
        )
    
    # Check if user is member of this committee
    is_member = any(member.email == current_user.email for member in committee.members)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    from datetime import datetime
    committee.status = VettingStatus.PENDING_APPROVAL
    committee.submitted_at = datetime.utcnow()
    committee.submitted_by = current_user.email
    
    db.commit()
    db.refresh(committee)
    return committee

@router.post("/{committee_id}/cancel-submission", response_model=VettingCommitteeResponse)
def cancel_submission(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel submission and return to open status (Committee members only)"""
    
    if current_user.role != UserRole.VETTING_COMMITTEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only committee members can cancel submission"
        )
    
    # Load committee with event relationship
    from app.models.event import Event
    committee = db.query(VettingCommittee).join(Event).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel submission for committees in pending approval status"
        )
    
    # Check if user is member of this committee
    is_member = any(member.email == current_user.email for member in committee.members)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Check if event has started or selection period has ended
    from datetime import datetime, date
    now = datetime.utcnow()
    today = now.date()
    
    # Check event start date
    if committee.event and committee.event.start_date:
        event_start = committee.event.start_date
        # Convert to date if it's a datetime object
        if isinstance(event_start, datetime):
            event_start = event_start.date()
        elif not isinstance(event_start, date):
            # Handle other types by converting to string then parsing
            try:
                event_start = datetime.strptime(str(event_start), '%Y-%m-%d').date()
            except:
                event_start = None
        
        if event_start and today >= event_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel submission after event has started"
            )
    
    # Check selection end date
    if committee.selection_end_date:
        selection_end = committee.selection_end_date
        # Convert to date if it's a datetime object
        if isinstance(selection_end, datetime):
            selection_end = selection_end.date()
        elif not isinstance(selection_end, date):
            # Handle other types by converting to string then parsing
            try:
                selection_end = datetime.strptime(str(selection_end), '%Y-%m-%d').date()
            except:
                selection_end = None
        
        if selection_end and today >= selection_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel submission after selection period has ended"
            )
    
    committee.status = VettingStatus.OPEN
    committee.submitted_at = None
    committee.submitted_by = None
    
    db.commit()
    db.refresh(committee)
    return committee

@router.post("/{committee_id}/approve-final", response_model=VettingCommitteeResponse)
def approve_final(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Final approval of committee selections (Approvers only)"""
    
    if current_user.role != UserRole.VETTING_APPROVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approvers can give final approval"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve committees in pending approval status"
        )
    
    # Check if user is approver for this committee
    if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    from datetime import datetime
    committee.status = VettingStatus.APPROVED
    committee.approved_at = datetime.utcnow()
    committee.approved_by = current_user.email
    
    db.commit()
    db.refresh(committee)
    return committee

@router.post("/{committee_id}/cancel-approval", response_model=VettingCommitteeResponse)
def cancel_approval(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel approval and return to pending approval status (Approvers only)"""
    
    if current_user.role not in [UserRole.APPROVER, UserRole.VETTING_APPROVER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only approvers can cancel approval"
        )
    
    # Load committee with event relationship
    from app.models.event import Event
    committee = db.query(VettingCommittee).join(Event).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    if committee.status != VettingStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel approval for approved committees"
        )
    
    # Check if user is approver for this committee
    if committee.approver_email != current_user.email and committee.approver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Check if event has started
    from datetime import datetime, date
    now = datetime.utcnow()
    today = now.date()
    
    if committee.event and committee.event.start_date:
        event_start = committee.event.start_date
        # Convert to date if it's a datetime object
        if isinstance(event_start, datetime):
            event_start = event_start.date()
        elif not isinstance(event_start, date):
            # Handle other types by converting to string then parsing
            try:
                event_start = datetime.strptime(str(event_start), '%Y-%m-%d').date()
            except:
                event_start = None
        
        if event_start and today >= event_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel approval after event has started"
            )
    
    committee.status = VettingStatus.PENDING_APPROVAL
    committee.approved_at = None
    committee.approved_by = None
    
    db.commit()
    db.refresh(committee)
    return committee

@router.delete("/{committee_id}")
def delete_vetting_committee(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete vetting committee (Admin only, only if open)"""
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete vetting committees"
        )
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found"
        )
    
    if committee.status != VettingStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete committees in open status"
        )
    
    db.delete(committee)
    db.commit()
    
    return {"message": "Vetting committee deleted successfully"}