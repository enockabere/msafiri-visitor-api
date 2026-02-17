"""Per diem request workflow approval endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest
from app.models.perdiem_approval_step import PerdiemApprovalStep
from app.models.approver import ApprovalWorkflow, ApprovalStep
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.core.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("/{request_id}/approvals")
async def get_perdiem_request_approvals(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approval workflow status for a per diem request"""
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching approvals for per diem request {request_id}")
    
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Per diem request not found")
    
    # Get all approvals for this per diem request
    approvals = (
        db.query(PerdiemApprovalStep, User, ApprovalStep)
        .join(User, PerdiemApprovalStep.approver_user_id == User.id)
        .outerjoin(ApprovalStep, PerdiemApprovalStep.workflow_step_id == ApprovalStep.id)
        .filter(PerdiemApprovalStep.perdiem_request_id == request_id)
        .order_by(PerdiemApprovalStep.step_order)
        .all()
    )
    
    result = []
    for approval, approver, step in approvals:
        result.append({
            "id": approval.id,
            "step_order": approval.step_order,
            "step_name": step.step_name if step else f"Approval Step {approval.step_order}",
            "approver_user_id": approval.approver_user_id,
            "approver_name": approver.full_name or approver.email,
            "approver_email": approver.email,
            "status": approval.status,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
        })
    
    return result


@router.post("/{request_id}/initialize-workflow")
async def initialize_perdiem_workflow(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialize approval workflow for per diem request after FinCo/Travel Admin approval"""
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing workflow for per diem request {request_id}")
    
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Per diem request not found")
    
    # Only approved requests can have workflow initialized
    if perdiem_request.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved per diem requests can initialize workflow")
    
    # Get participant and event to find tenant
    participant = db.query(EventParticipant).filter(EventParticipant.id == perdiem_request.participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    tenant_id = event.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Event has no tenant assigned")
    
    # Get tenant to find slug
    from app.models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
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
    
    if not workflow:
        logger.warning(f"No active PER_DIEM workflow found for tenant {tenant.slug} (id: {tenant_id})")
        raise HTTPException(status_code=400, detail="No active approval workflow found for per diem requests")
    
    # Get workflow steps
    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.workflow_id == workflow.id)
        .order_by(ApprovalStep.step_order)
        .all()
    )
    
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow has no steps configured")
    
    # Delete existing approval records if reinitializing
    db.query(PerdiemApprovalStep).filter(PerdiemApprovalStep.perdiem_request_id == perdiem_request.id).delete()
    
    # Create approval records
    for step in steps:
        approval = PerdiemApprovalStep(
            perdiem_request_id=perdiem_request.id,
            workflow_step_id=step.id,
            step_order=step.step_order,
            approver_user_id=step.approver_user_id,
            status="OPEN" if step.step_order == 1 else "PENDING"
        )
        db.add(approval)
    
    logger.info(f"Created {len(steps)} approval steps for per diem request {request_id}")
    
    db.commit()
    
    return {"message": "Workflow initialized successfully", "steps": len(steps)}


@router.post("/{request_id}/approve")
async def approve_perdiem_workflow_step(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve current workflow step for per diem request"""
    logger = logging.getLogger(__name__)
    logger.info(f"User {current_user.id} approving per diem request {request_id}")
    
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Per diem request not found")
    
    # Find the current user's OPEN approval step
    approval_step = (
        db.query(PerdiemApprovalStep)
        .filter(
            PerdiemApprovalStep.perdiem_request_id == request_id,
            PerdiemApprovalStep.approver_user_id == current_user.id,
            PerdiemApprovalStep.status == "OPEN"
        )
        .first()
    )
    
    if not approval_step:
        raise HTTPException(status_code=403, detail="No pending approval step found for current user")
    
    # Mark this step as approved
    approval_step.status = "APPROVED"
    approval_step.approved_at = datetime.utcnow()
    
    # Check if there are more steps
    next_step = (
        db.query(PerdiemApprovalStep)
        .filter(
            PerdiemApprovalStep.perdiem_request_id == request_id,
            PerdiemApprovalStep.step_order > approval_step.step_order
        )
        .order_by(PerdiemApprovalStep.step_order)
        .first()
    )
    
    if next_step:
        # Open the next step
        next_step.status = "OPEN"
        logger.info(f"Opened next approval step {next_step.step_order} for per diem request {request_id}")
    else:
        # All steps approved - mark request as issued
        perdiem_request.status = "issued"
        logger.info(f"All approval steps completed for per diem request {request_id}, marked as issued")
    
    db.commit()
    
    return {"message": "Approval step completed successfully", "status": perdiem_request.status}


@router.post("/{request_id}/reject")
async def reject_perdiem_workflow_step(
    request_id: int,
    rejection_reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject current workflow step for per diem request"""
    logger = logging.getLogger(__name__)
    logger.info(f"User {current_user.id} rejecting per diem request {request_id}")
    
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Per diem request not found")
    
    # Find the current user's OPEN approval step
    approval_step = (
        db.query(PerdiemApprovalStep)
        .filter(
            PerdiemApprovalStep.perdiem_request_id == request_id,
            PerdiemApprovalStep.approver_user_id == current_user.id,
            PerdiemApprovalStep.status == "OPEN"
        )
        .first()
    )
    
    if not approval_step:
        raise HTTPException(status_code=403, detail="No pending approval step found for current user")
    
    # Mark this step as rejected
    approval_step.status = "REJECTED"
    approval_step.rejected_at = datetime.utcnow()
    approval_step.rejection_reason = rejection_reason
    
    # Mark all remaining steps as PENDING (reset)
    db.query(PerdiemApprovalStep).filter(
        PerdiemApprovalStep.perdiem_request_id == request_id,
        PerdiemApprovalStep.step_order > approval_step.step_order
    ).update({"status": "PENDING"})
    
    # Mark request as rejected
    perdiem_request.status = "rejected"
    perdiem_request.rejected_by = current_user.email
    perdiem_request.rejected_at = datetime.utcnow()
    perdiem_request.rejection_reason = rejection_reason
    
    logger.info(f"Per diem request {request_id} rejected at step {approval_step.step_order}")
    
    db.commit()
    
    return {"message": "Per diem request rejected", "status": perdiem_request.status}
