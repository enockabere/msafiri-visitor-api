# File: app/services/vetting_email_service.py
from app.core.email_service import email_service
from app.models.vetting_committee import VettingCommittee, VettingCommitteeMember
from app.models.event import Event
from typing import List

def send_vetting_committee_invitations(
    committee: VettingCommittee,
    event: Event,
    members: List[VettingCommitteeMember],
    frontend_url: str
):
    """Send invitation emails to vetting committee members"""
    
    for member in members:
        subject = f"Invitation: Vetting Committee for {event.title}"
        
        message = f"""
Dear {member.full_name},

You have been invited to join the vetting committee for the event: {event.title}

Event Details:
- Event: {event.title}
- Date: {event.start_date} to {event.end_date}
- Location: {event.location}

Selection Period:
- Start: {committee.selection_start_date}
- End: {committee.selection_end_date}

Your Role:
As a vetting committee member, you will review and select participants for this event. You will have access to the participant list and can approve or reject applications.

Access the Portal:
{frontend_url}/vetting-committee/{committee.id}

Login with your email: {member.email}
You will be prompted to set a password on first login.

Please complete your selections before {committee.selection_end_date}.

Best regards,
MSF Msafiri Team
        """
        
        try:
            email_service.send_notification_email(
                to_email=member.email,
                user_name=member.full_name,
                title=subject,
                message=message
            )
        except Exception as e:
            print(f"Failed to send invitation to {member.email}: {e}")

def send_approver_notification(
    committee: VettingCommittee,
    event: Event,
    approver_email: str,
    frontend_url: str
):
    """Send notification to approver when selections are submitted"""
    
    subject = f"Approval Required: Participant Selections for {event.title}"
    
    message = f"""
Dear Approver,

The vetting committee has submitted their participant selections for: {event.title}

Event Details:
- Event: {event.title}
- Date: {event.start_date} to {event.end_date}
- Submitted: {committee.submitted_at}

Your Action Required:
Please review and approve the participant selections.

Access the Portal:
{frontend_url}/approver/{committee.id}

Login with your email: {approver_email}

Best regards,
MSF Msafiri Team
    """
    
    try:
        email_service.send_notification_email(
            to_email=approver_email,
            user_name="Approver",
            title=subject,
            message=message
        )
    except Exception as e:
        print(f"Failed to send approver notification to {approver_email}: {e}")

def send_approval_confirmation(
    committee: VettingCommittee,
    event: Event,
    frontend_url: str
):
    """Send confirmation when selections are approved"""
    
    subject = f"Approved: Participant Selections for {event.title}"
    
    message = f"""
Dear Team,

The participant selections for {event.title} have been approved.

Event Details:
- Event: {event.title}
- Approved: {committee.approved_at}
- Approved by: {committee.approved_by}

Selected participants will now be able to see the event in the mobile app.

Best regards,
MSF Msafiri Team
    """
    
    # Send to committee members
    for member in committee.members:
        try:
            email_service.send_notification_email(
                to_email=member.email,
                user_name=member.full_name,
                title=subject,
                message=message
            )
        except Exception as e:
            print(f"Failed to send confirmation to {member.email}: {e}")
