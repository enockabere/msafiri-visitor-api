from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.models import VettingMemberSelection, VettingCommittee, EventParticipant, VettingMemberComment
from app.schemas.vetting_member_selection import (
    VettingMemberSelectionCreate, VettingMemberSelectionResponse,
    VettingMemberCommentCreate, VettingMemberCommentResponse, VettingMemberCommentsListResponse
)
from app.core.deps import get_current_user
from app.models.user import User, UserRole

router = APIRouter()


@router.post("/events/{event_id}/vetting-selections", response_model=VettingMemberSelectionResponse)
def create_or_update_member_selection(
    event_id: int,
    selection_data: VettingMemberSelectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update a vetting member's selection for a participant"""
    
    # Verify user is a vetting committee member for this event
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()
    
    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )
    
    # Check if user is a committee member
    is_member = any(member.email == current_user.email for member in vetting_committee.members)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of the vetting committee"
        )
    
    # Verify participant exists
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == selection_data.participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    # Check if selection already exists
    existing_selection = db.query(VettingMemberSelection).filter(
        VettingMemberSelection.event_id == event_id,
        VettingMemberSelection.participant_id == selection_data.participant_id,
        VettingMemberSelection.member_email == current_user.email
    ).first()
    
    if existing_selection:
        # Update existing selection
        existing_selection.selection = selection_data.selection
        existing_selection.comments = selection_data.comments
        db.commit()
        db.refresh(existing_selection)
        return existing_selection
    else:
        # Create new selection
        new_selection = VettingMemberSelection(
            event_id=event_id,
            participant_id=selection_data.participant_id,
            member_email=current_user.email,
            selection=selection_data.selection,
            comments=selection_data.comments
        )
        db.add(new_selection)
        db.commit()
        db.refresh(new_selection)
        return new_selection


@router.get("/events/{event_id}/vetting-selections", response_model=List[VettingMemberSelectionResponse])
def get_event_vetting_selections(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all vetting selections for an event"""
    
    # Verify user has access to vetting data
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()
    
    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )
    
    # Check if user is a committee member or approver
    is_member = any(member.email == current_user.email for member in vetting_committee.members)
    is_approver = any(approver.email == current_user.email for approver in vetting_committee.approvers)
    
    if not (is_member or is_approver):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to vetting data"
        )
    
    selections = db.query(VettingMemberSelection).filter(
        VettingMemberSelection.event_id == event_id
    ).all()
    
    return selections


@router.get("/events/{event_id}/participants/{participant_id}/vetting-selections")
def get_participant_vetting_selections(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all vetting selections for a specific participant"""

    # Verify access
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )

    is_member = any(member.email == current_user.email for member in vetting_committee.members)
    is_approver = any(approver.email == current_user.email for approver in vetting_committee.approvers)

    if not (is_member or is_approver):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to vetting data"
        )

    selections = db.query(VettingMemberSelection).filter(
        VettingMemberSelection.event_id == event_id,
        VettingMemberSelection.participant_id == participant_id
    ).all()

    # Group selections by member
    member_selections = {}
    for selection in selections:
        member_selections[selection.member_email] = {
            "selection": selection.selection,
            "comments": selection.comments,
            "created_at": selection.created_at,
            "updated_at": selection.updated_at
        }

    # Get all committee members to show who hasn't voted yet
    all_members = [member.email for member in vetting_committee.members]

    return {
        "participant_id": participant_id,
        "member_selections": member_selections,
        "all_members": all_members,
        "total_members": len(all_members),
        "selections_count": len(member_selections)
    }


@router.get("/events/{event_id}/vetting-selections-summary")
def get_vetting_selections_summary(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get a summary of all vetting selections for an event with committee member info.

    Returns committee members and all their selections grouped by participant.
    Used by the Selections tab to display individual member columns.
    """
    # Verify access
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )

    # Check if user is a committee member, approver, or admin
    is_member = any(member.email.lower() == current_user.email.lower() for member in vetting_committee.members)
    is_approver = any(approver.email.lower() == current_user.email.lower() for approver in vetting_committee.approvers)

    # Also check legacy approver field
    if not is_approver and vetting_committee.approver_email:
        is_approver = vetting_committee.approver_email.lower() == current_user.email.lower()

    # Allow admins access
    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]

    if not (is_member or is_approver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to vetting data"
        )

    # Get all committee members
    committee_members = [
        {
            "email": member.email,
            "full_name": member.full_name
        }
        for member in vetting_committee.members
    ]

    # Get all selections
    selections = db.query(VettingMemberSelection).filter(
        VettingMemberSelection.event_id == event_id
    ).all()

    # Group selections by participant_id, then by member_email
    selections_by_participant: Dict[int, Dict[str, Any]] = {}
    for selection in selections:
        if selection.participant_id not in selections_by_participant:
            selections_by_participant[selection.participant_id] = {}

        selections_by_participant[selection.participant_id][selection.member_email] = {
            "selection": selection.selection,
            "comments": selection.comments,
            "updated_at": selection.updated_at.isoformat() if selection.updated_at else None
        }

    return {
        "event_id": event_id,
        "committee_status": vetting_committee.status.value,
        "committee_members": committee_members,
        "selections_by_participant": selections_by_participant,
        "current_user_email": current_user.email,
        "current_user_is_member": is_member,
        "current_user_is_approver": is_approver
    }


@router.post("/events/{event_id}/participants/{participant_id}/vetting-comments", response_model=VettingMemberCommentResponse)
def create_vetting_comment(
    event_id: int,
    participant_id: int,
    comment_data: VettingMemberCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to a participant's vetting discussion.

    Both committee members and approvers can add comments.
    Comments are stored with author info and role for full history tracking.
    """
    # Verify access
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )

    # Check if user is a committee member or approver
    is_member = any(member.email.lower() == current_user.email.lower() for member in vetting_committee.members)
    is_approver = any(approver.email.lower() == current_user.email.lower() for approver in vetting_committee.approvers)

    # Also check legacy approver field
    if not is_approver and vetting_committee.approver_email:
        is_approver = vetting_committee.approver_email.lower() == current_user.email.lower()

    # Allow admins access
    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]

    if not (is_member or is_approver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to add vetting comments"
        )

    # Verify participant exists
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    # Determine author role
    if is_approver:
        author_role = "approver"
    elif is_member:
        author_role = "committee_member"
    else:
        author_role = "admin"

    # Get author name from committee or user
    author_name = current_user.full_name or current_user.email
    if is_member:
        for member in vetting_committee.members:
            if member.email.lower() == current_user.email.lower():
                author_name = member.full_name
                break
    elif is_approver:
        for approver in vetting_committee.approvers:
            if approver.email.lower() == current_user.email.lower():
                author_name = approver.full_name
                break

    # Create comment
    new_comment = VettingMemberComment(
        event_id=event_id,
        participant_id=participant_id,
        author_email=current_user.email,
        author_name=author_name,
        author_role=author_role,
        comment=comment_data.comment
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment


@router.get("/events/{event_id}/participants/{participant_id}/vetting-comments", response_model=VettingMemberCommentsListResponse)
def get_participant_vetting_comments(
    event_id: int,
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all comments for a participant's vetting discussion.

    Returns comments in chronological order (oldest first) so users can scroll up to see history.
    """
    # Verify access
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()

    if not vetting_committee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting committee not found for this event"
        )

    # Check if user is a committee member or approver
    is_member = any(member.email.lower() == current_user.email.lower() for member in vetting_committee.members)
    is_approver = any(approver.email.lower() == current_user.email.lower() for approver in vetting_committee.approvers)

    # Also check legacy approver field
    if not is_approver and vetting_committee.approver_email:
        is_approver = vetting_committee.approver_email.lower() == current_user.email.lower()

    # Allow admins access
    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]

    if not (is_member or is_approver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to vetting comments"
        )

    # Get all comments, ordered by created_at ascending (oldest first)
    comments = db.query(VettingMemberComment).filter(
        VettingMemberComment.event_id == event_id,
        VettingMemberComment.participant_id == participant_id
    ).order_by(VettingMemberComment.created_at.asc()).all()

    return {
        "participant_id": participant_id,
        "comments": comments,
        "total_count": len(comments)
    }
