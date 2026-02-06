from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.event import Event
from app.api.deps import get_current_user
from app.core.email_service import email_service
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class VettingSubmission(BaseModel):
    event_id: int
    submitted_by: str

class VettingStatus(BaseModel):
    status: str
    submitted_at: Optional[str] = None
    submitted_by: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None

@router.post("/events/{event_id}/vetting/submit")
async def submit_vetting(
    event_id: int,
    submission: VettingSubmission,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit vetting for approval and notify approver"""
    try:
        from app.models.vetting_committee import VettingCommittee, VettingStatus
        from datetime import datetime
        
        # Get event details
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update vetting committee status
        committee = db.query(VettingCommittee).filter(
            VettingCommittee.event_id == event_id
        ).first()
        
        if committee:
            committee.status = VettingStatus.PENDING_APPROVAL
            committee.submitted_at = datetime.utcnow()
            committee.submitted_by = current_user.email
            db.commit()
        else:
            raise HTTPException(status_code=404, detail="Vetting committee not found")
        
        # Find vetting approvers for this event
        # Get approver from committee
        if committee.approver_id:
            approver = db.query(User).filter(User.id == committee.approver_id).first()
            approvers = [approver] if approver else []
        else:
            # Fallback: find all users with vetting_approver role
            from app.models.user_roles import UserRole
            approver_role_records = db.query(UserRole).filter(
                UserRole.role == "VETTING_APPROVER"
            ).all()
            approver_ids = [record.user_id for record in approver_role_records]
            approvers = db.query(User).filter(
                User.id.in_(approver_ids)
            ).all()
        
        # Send email notification to approvers
        for approver in approvers:
            background_tasks.add_task(
                send_vetting_notification,
                approver.email,
                event.title,
                current_user.full_name or current_user.email
            )
        
        logger.info(f"✅ VETTING SUBMITTED: Event {event.title} by {current_user.email}")
        logger.info(f"📧 NOTIFYING {len(approvers)} APPROVERS")
        
        return {
            "message": "Vetting submitted successfully",
            "status": "submitted",
            "approvers_notified": len(approvers)
        }
        
    except Exception as e:
        logger.error(f"❌ VETTING SUBMISSION ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit vetting")

@router.get("/events/{event_id}/vetting/status")
async def get_vetting_status(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get vetting status for an event"""
    try:
        from app.models.vetting_committee import VettingCommittee, VettingStatus

        # Check database for vetting committee status
        committee = db.query(VettingCommittee).filter(
            VettingCommittee.event_id == event_id
        ).first()

        if not committee:
            return {"status": "not_submitted"}

        # Map database status to frontend status
        status_map = {
            VettingStatus.OPEN: "not_submitted",
            VettingStatus.PENDING_APPROVAL: "submitted", 
            VettingStatus.APPROVED: "approved"
        }

        status = status_map.get(committee.status, "not_submitted")

        return {
            "status": status,
            "submitted_at": committee.submitted_at.isoformat() if committee.submitted_at else None,
            "submitted_by": committee.submitted_by,
            "approved_at": committee.approved_at.isoformat() if committee.approved_at else None,
            "approved_by": committee.approved_by
        }

    except Exception as e:
        logger.error(f"❌ VETTING STATUS ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get vetting status")

class VettingApprovalRequest(BaseModel):
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

@router.get("/events/{event_id}/participants/count")
async def get_participants_count(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get participant count for debugging"""
    try:
        from app.models.event_participant import EventParticipant
        
        participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id
        ).all()
        
        return {
            "event_id": event_id,
            "participant_count": len(participants),
            "participants": [
                {
                    "email": p.email,
                    "name": p.full_name,
                    "status": p.status
                } for p in participants
            ],
            "send_emails_enabled": settings.SEND_EMAILS
        }
        
    except Exception as e:
        logger.error(f"❌ PARTICIPANTS COUNT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get participants count")

@router.post("/events/{event_id}/vetting/cancel-approval")
async def cancel_vetting_approval(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel vetting approval and reset to pending status"""
    try:
        from app.models.vetting_committee import VettingCommittee, VettingStatus
        
        # Check if user is vetting approver
        from app.models.user_roles import UserRole
        
        is_approver = current_user.role in ["VETTING_APPROVER", "vetting_approver"]
        if not is_approver:
            approver_role = db.query(UserRole).filter(
                UserRole.user_id == current_user.id,
                UserRole.role == "VETTING_APPROVER"
            ).first()
            is_approver = approver_role is not None

        if not is_approver:
            raise HTTPException(status_code=403, detail="Only vetting approvers can cancel approval")
        
        # Get vetting committee
        committee = db.query(VettingCommittee).filter(
            VettingCommittee.event_id == event_id
        ).first()

        if not committee:
            raise HTTPException(status_code=400, detail="No vetting committee found for this event")
        
        # Reset to pending approval status
        committee.status = VettingStatus.PENDING_APPROVAL
        committee.approved_at = None
        committee.approved_by = None
        db.commit()
        
        logger.info(f"✅ VETTING APPROVAL CANCELLED: Event {event_id} by {current_user.email}")
        
        return {
            "message": "Vetting approval cancelled successfully",
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"❌ VETTING CANCEL APPROVAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel vetting approval")

@router.post("/events/{event_id}/vetting/approve")
async def approve_vetting(
    event_id: int,
    background_tasks: BackgroundTasks,
    approval_data: Optional[VettingApprovalRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve vetting submission and send emails to participants"""
    print(f"🚀 VETTING APPROVAL API CALLED - Event ID: {event_id}, User: {current_user.email}")
    try:
        from app.models.vetting_committee import VettingCommittee, VettingStatus, ApprovalStatus
        from app.models.event_participant import EventParticipant
        from app.models.event import Event
        from datetime import datetime
        
        # Check if user is vetting approver (check both primary role and secondary roles)
        from app.models.user_roles import UserRole
        
        print(f"🔍 CHECKING APPROVER PERMISSIONS for user {current_user.email}")
        print(f"🔍 User primary role: {current_user.role}")

        is_approver = current_user.role in ["VETTING_APPROVER", "vetting_approver"]
        print(f"🔍 Primary role check: {is_approver}")
        
        if not is_approver:
            # Check secondary roles
            print(f"🔍 Checking secondary roles for user ID {current_user.id}")
            approver_role = db.query(UserRole).filter(
                UserRole.user_id == current_user.id,
                UserRole.role == "VETTING_APPROVER"
            ).first()
            is_approver = approver_role is not None
            print(f"🔍 Secondary role check: {is_approver}")

        if not is_approver:
            print(f"❌ ACCESS DENIED: User {current_user.email} is not a vetting approver")
            raise HTTPException(status_code=403, detail="Only vetting approvers can approve")
            
        print(f"✅ APPROVER PERMISSIONS VERIFIED for {current_user.email}")
        
        # Get event details
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get vetting committee
        committee = db.query(VettingCommittee).filter(
            VettingCommittee.event_id == event_id
        ).first()

        if not committee:
            raise HTTPException(status_code=400, detail="No vetting committee found for this event")
            
        print(f"🔍 COMMITTEE STATUS: {committee.status}")
        
        # Check if already approved
        if committee.status == VettingStatus.APPROVED:
            print(f"ℹ️ VETTING ALREADY APPROVED: Status is {committee.status}")
            return {
                "message": "Vetting already approved",
                "status": "approved",
                "participants_notified": 0
            }
        
        # Allow approval for multiple statuses to handle different workflow states
        allowed_statuses = [VettingStatus.PENDING_APPROVAL, VettingStatus.OPEN]
        if committee.status not in allowed_statuses:
            print(f"❌ INVALID STATUS: Current status {committee.status} not in allowed statuses {allowed_statuses}")
            raise HTTPException(status_code=400, detail=f"Vetting is not ready for approval. Current status: {committee.status}")
        
        print(f"✅ STATUS CHECK PASSED: {committee.status} is allowed for approval")

        # Verify this user is the designated approver for this committee
        if committee.approver_id and committee.approver_id != current_user.id:
            print(f"❌ WRONG APPROVER: Committee approver_id={committee.approver_id}, current_user.id={current_user.id}")
            raise HTTPException(status_code=403, detail="You are not the designated approver for this vetting committee")
        print(f"✅ APPROVER VERIFICATION PASSED")
        
        # Update committee status
        print(f"📝 UPDATING DATABASE - Setting status to APPROVED")
        committee.status = VettingStatus.APPROVED
        try:
            committee.approval_status = ApprovalStatus.APPROVED
        except:
            # ApprovalStatus might not exist, skip it
            pass
        committee.approved_at = datetime.utcnow()
        committee.approved_by = current_user.email
        db.commit()
        print(f"✅ DATABASE UPDATED - Committee status saved")
        
        # Get all participants (selected and not selected)
        all_participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id
        ).all()
        
        print(f"🔍 Found {len(all_participants)} participants")
        logger.info(f"🔍 PARTICIPANTS QUERY: Found {len(all_participants)} participants for event {event_id}")
        for i, participant in enumerate(all_participants):
            print(f"🔍 PARTICIPANT {i+1}: {participant.email} - {participant.full_name} - Status: {participant.status}")
            logger.info(f"🔍 PARTICIPANT {i+1}: {participant.email} - {participant.full_name} - Status: {participant.status}")
        
        # Get tenant slug for template
        try:
            tenant_slug = event.tenant.slug if hasattr(event, 'tenant') and event.tenant else "default"
        except:
            tenant_slug = "default"

        
        # Load custom email template or use default
        custom_subject = approval_data.email_subject if approval_data else None
        custom_body = approval_data.email_body if approval_data else None
        print(f"🔍 EMAIL TEMPLATE: Subject={custom_subject is not None}, Body={custom_body is not None}")

        logger.info(f"🔍 EMAIL TEMPLATE: Subject={custom_subject is not None}, Body={custom_body is not None}")
        logger.info(f"🔍 EMAIL SETTINGS: SEND_EMAILS={settings.SEND_EMAILS}")
        
        # Test email service
        try:
            print(f"🧪 TESTING EMAIL SERVICE")
            test_result = email_service.send_email(
                to_emails=["test@example.com"],
                subject="Test Email",
                html_content="This is a test"
            )
            print(f"🧪 EMAIL SERVICE TEST RESULT: {test_result}")
            logger.info(f"🔍 EMAIL SERVICE TEST: {test_result}")
        except Exception as e:
            print(f"🧪 EMAIL SERVICE TEST FAILED: {str(e)}")
            logger.error(f"❌ EMAIL SERVICE TEST FAILED: {str(e)}")
        
        # Send emails to all participants (synchronously for debugging)

        emails_sent = 0
        for participant in all_participants:
            print(f"📧 PROCESSING EMAIL for {participant.email} with status {participant.status}")
            try:
                await send_participant_notification(
                    participant.email,
                    participant.full_name,
                    participant.status,
                    getattr(event, 'title', 'Event'),
                    getattr(event, 'location', '') or "",
                    f"{getattr(event, 'start_date', '')} - {getattr(event, 'end_date', '')}" if getattr(event, 'start_date', None) and getattr(event, 'end_date', None) else "",
                    tenant_slug,
                    custom_subject,
                    custom_body
                )
                emails_sent += 1
                print(f"✅ EMAIL SENT SUCCESSFULLY to {participant.email}")
            except Exception as e:
                print(f"❌ FAILED TO SEND EMAIL to {participant.email}: {str(e)}")
                import traceback
                print(f"❌ EMAIL ERROR TRACEBACK: {traceback.format_exc()}")
        
        print(f"✅ Emails sent: {emails_sent}/{len(all_participants)}")
        
        print(f"✅ VETTING APPROVED by {current_user.email}")
        print(f"📧 NOTIFICATION PROCESS COMPLETE for {len(all_participants)} participants")
        
        result = {
            "message": "Vetting approved successfully",
            "status": "approved",
            "participants_notified": emails_sent,
            "total_participants": len(all_participants)
        }
        print(f"🎉 VETTING APPROVAL COMPLETE - Returning: {result}")
        print(f"🔙 FUNCTION RETURNING TO FRONTEND")
        return result
        
    except Exception as e:
        logger.error(f"❌ VETTING APPROVAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to approve vetting")

async def send_vetting_notification(approver_email: str, event_title: str, submitted_by: str):
    """Send email notification to vetting approver"""
    try:
        subject = f"Vetting Approval Required - {event_title}"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ee0000, #ff4444); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">Vetting Approval Required</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333; margin-bottom: 20px;">Event Vetting Submitted</h2>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <p><strong>Event:</strong> {event_title}</p>
                    <p><strong>Submitted by:</strong> {submitted_by}</p>
                    <p><strong>Status:</strong> Awaiting your approval</p>
                </div>
                
                <p style="color: #666; line-height: 1.6;">
                    The vetting committee has completed their review of event participants and submitted 
                    the vetting for your approval. Please log in to the admin portal to review and approve 
                    the vetting.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}" 
                       style="background: #ee0000; color: white; padding: 12px 30px; text-decoration: none; 
                              border-radius: 5px; font-weight: bold; display: inline-block;">
                        Review Vetting
                    </a>
                </div>
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    MSF Msafiri Admin Portal
                </p>
            </div>
        </div>
        """
        
        email_service.send_email(
            to_emails=[approver_email],
            subject=subject,
            html_content=html_content
        )
        
        logger.info(f"📧 VETTING NOTIFICATION SENT to {approver_email}")
        
    except Exception as e:
        logger.error(f"❌ FAILED TO SEND VETTING NOTIFICATION to {approver_email}: {str(e)}")

async def send_participant_notification(
    participant_email: str,
    participant_name: str, 
    participant_status: str,
    event_title: str,
    event_location: str,
    event_date_range: str,
    tenant_slug: str,
    custom_subject: Optional[str] = None,
    custom_body: Optional[str] = None
):
    """Send notification to participant based on their selection status"""
    try:
        print(f"📧 SEND_PARTICIPANT_NOTIFICATION CALLED for {participant_email}")
        logger.info(f"📧 STARTING EMAIL SEND to {participant_email} (status: {participant_status})")
        # Use custom template if provided, otherwise use default
        if custom_subject and custom_body:
            subject = custom_subject
            body = custom_body
        else:
            # Default template
            subject = f"Event Selection Results - {event_title}"
            body = f"""Dear {participant_name},

We have completed the selection process for {event_title}.

{"🎉 Congratulations! You have been selected to participate." if participant_status == 'selected' else "Thank you for your interest. Unfortunately, you have not been selected for this event."}

Event Details:
• Event: {event_title}
• Location: {event_location}
• Date: {event_date_range}

{"Next Steps: Please check the Msafiri mobile app for further instructions." if participant_status == 'selected' else "We encourage you to apply for future events."}

Best regards,
The Event Organization Team"""
        
        # Replace template variables
        subject = subject.replace('{{PARTICIPANT_NAME}}', participant_name)
        subject = subject.replace('{{EVENT_TITLE}}', event_title)
        subject = subject.replace('{{EVENT_LOCATION}}', event_location)
        subject = subject.replace('{{EVENT_DATE_RANGE}}', event_date_range)
        subject = subject.replace('{{PARTICIPANT_EMAIL}}', participant_email)
        
        # Handle conditional content in body
        if participant_status == 'selected':
            # Show selected content, hide not selected content
            import re
            body = re.sub(r'{{#if_not_selected}}.*?{{/if_not_selected}}', '', body, flags=re.DOTALL)
            body = re.sub(r'{{#if_selected}}(.*?){{/if_selected}}', r'\1', body, flags=re.DOTALL)
        else:
            # Show not selected content, hide selected content  
            import re
            body = re.sub(r'{{#if_selected}}.*?{{/if_selected}}', '', body, flags=re.DOTALL)
            body = re.sub(r'{{#if_not_selected}}(.*?){{/if_not_selected}}', r'\1', body, flags=re.DOTALL)
        
        # Replace remaining variables
        body = body.replace('{{PARTICIPANT_NAME}}', participant_name)
        body = body.replace('{{EVENT_TITLE}}', event_title)
        body = body.replace('{{EVENT_LOCATION}}', event_location)
        body = body.replace('{{EVENT_DATE_RANGE}}', event_date_range)
        body = body.replace('{{PARTICIPANT_EMAIL}}', participant_email)
        
        print(f"📧 CALLING EMAIL SERVICE for {participant_email}")
        result = email_service.send_email(
            to_emails=[participant_email],
            subject=subject,
            html_content=body.replace('\n', '<br>')
        )
        print(f"📧 EMAIL SERVICE RESULT for {participant_email}: {result}")
        
        if result:
            print(f"✅ EMAIL SERVICE SUCCESS for {participant_email}")
            logger.info(f"✅ PARTICIPANT NOTIFICATION SENT to {participant_email} (status: {participant_status})")
        else:
            print(f"❌ EMAIL SERVICE FAILED for {participant_email}")
            logger.error(f"❌ FAILED TO SEND EMAIL to {participant_email} - email_service returned False")
        
    except Exception as e:
        print(f"💥 EMAIL SEND EXCEPTION for {participant_email}: {str(e)}")
        logger.error(f"❌ FAILED TO SEND PARTICIPANT NOTIFICATION to {participant_email}: {str(e)}")
        import traceback
        print(f"💥 EMAIL SEND TRACEBACK: {traceback.format_exc()}")
        logger.error(f"❌ EMAIL SEND TRACEBACK: {traceback.format_exc()}")
