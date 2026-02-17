from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event import Event
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.perdiem_request import PerdiemApprovalAction
from app.core.deps import get_current_user
from app.services.email_service import send_email
from app.services.notification_service import create_notification
from datetime import datetime
from typing import List

router = APIRouter()

@router.get("/pending")
async def get_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending per diem requests for approval by current user"""
    requests = db.query(PerdiemRequest).join(
        Event, PerdiemRequest.participant_id == Event.id
    ).filter(
        PerdiemRequest.approver_email == current_user.email,
        PerdiemRequest.status == PerdiemStatus.PENDING
    ).all()
    
    return requests

@router.post("/{request_id}/approve")
async def approve_perdiem(
    request_id: int,
    action: PerdiemApprovalAction,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject a per diem request (FinCo/Travel Admin approval)"""
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.approver_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to approve this request")
    
    if action.action == "approve":
        request.status = PerdiemStatus.APPROVED
        request.approved_by = current_user.email
        request.approved_at = datetime.utcnow()
        
        # Initialize workflow after FinCo/Travel Admin approval
        from app.models.approver import ApprovalWorkflow, ApprovalStep
        from app.models.perdiem_approval_step import PerdiemApprovalStep
        from app.models.event_participant import EventParticipant
        from app.models.event import Event
        from app.models.tenant import Tenant
        
        # Get participant and event to find tenant
        participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
        if participant:
            event = db.query(Event).filter(Event.id == participant.event_id).first()
            if event and event.tenant_id:
                # Get tenant to find slug
                tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first()
                if tenant:
                    # Get active workflow for PER_DIEM using tenant slug
                    workflow = (
                        db.query(ApprovalWorkflow)
                        .filter(
                            ApprovalWorkflow.tenant_id == tenant.slug,
                            ApprovalWorkflow.workflow_type == "PER_DIEM",
                            ApprovalWorkflow.is_active == True
                        )
                        .first()
                    )
                    
                    if workflow:
                        # Get workflow steps
                        steps = (
                            db.query(ApprovalStep)
                            .filter(ApprovalStep.workflow_id == workflow.id)
                            .order_by(ApprovalStep.step_order)
                            .all()
                        )
                        
                        if steps:
                            # Delete existing approval records if reinitializing
                            db.query(PerdiemApprovalStep).filter(PerdiemApprovalStep.perdiem_request_id == request.id).delete()
                            
                            # Create approval records
                            for step in steps:
                                approval = PerdiemApprovalStep(
                                    perdiem_request_id=request.id,
                                    workflow_step_id=step.id,
                                    step_order=step.step_order,
                                    approver_user_id=step.approver_user_id,
                                    status="OPEN" if step.step_order == 1 else "PENDING"
                                )
                                db.add(approval)
        
        # Send approval email
        background_tasks.add_task(
            send_approval_email,
            request,
            "approved",
            current_user.email,
            db
        )
        
    elif action.action == "reject":
        request.status = PerdiemStatus.REJECTED
        request.rejected_by = current_user.email
        request.rejected_at = datetime.utcnow()
        request.rejection_reason = action.rejection_reason
        
        # Send rejection email
        background_tasks.add_task(
            send_approval_email,
            request,
            "rejected",
            current_user.email,
            db
        )
    
    db.commit()
    return {"message": f"Request {action.action}d successfully"}

async def send_approval_email(request: PerdiemRequest, action: str, approver_email: str, db: Session):
    """Send email notification for approval/rejection"""
    participant = db.query(Event).filter(Event.id == request.participant_id).first()
    if not participant:
        return
    
    # Get tenant and finance admins
    tenant = db.query(Tenant).filter(Tenant.id == participant.tenant_id).first()
    finance_admins = db.query(User).filter(
        User.role.in_(["FINANCE_ADMIN", "finance_admin"])
    ).all()
    
    subject = f"Per Diem Request {action.title()}"
    
    # Email to requester
    await send_email(
        to_email=request.email,
        subject=subject,
        template="perdiem_approval_notification",
        context={
            "action": action,
            "request": request,
            "event": participant,
            "approver_email": approver_email
        }
    )
    
    # Email to finance admins
    for admin in finance_admins:
        await send_email(
            to_email=admin.email,
            subject=f"Per Diem Request {action.title()} - {participant.title}",
            template="perdiem_approval_notification",
            context={
                "action": action,
                "request": request,
                "event": participant,
                "approver_email": approver_email,
                "is_admin": True
            }
        )
        
        # Create notification for admin
        await create_notification(
            user_id=admin.id,
            title=f"Per Diem Request {action.title()}",
            message=f"Per diem request for {participant.title} has been {action}",
            type="perdiem_approval",
            tenant_id=tenant.id if tenant else None
        )
