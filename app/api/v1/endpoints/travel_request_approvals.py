"""Travel request approval workflow endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.travel_request import TravelRequest
from app.models.travel_request_approval_step import TravelRequestApprovalStep
from app.models.approver import ApprovalWorkflow, ApprovalStep
from app.models.user import User
from app.core.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("/{request_id}/approvals")
async def get_travel_request_approvals(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approval status for a travel request"""
    travel_request = db.query(TravelRequest).filter(TravelRequest.id == request_id).first()
    if not travel_request:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    # Get all approvals for this travel request
    approvals = (
        db.query(TravelRequestApprovalStep, User, ApprovalStep)
        .join(User, TravelRequestApprovalStep.approver_user_id == User.id)
        .join(ApprovalStep, TravelRequestApprovalStep.workflow_step_id == ApprovalStep.id)
        .filter(TravelRequestApprovalStep.travel_request_id == request_id)
        .order_by(TravelRequestApprovalStep.step_order)
        .all()
    )
    
    result = []
    for approval, approver, step in approvals:
        result.append({
            "id": approval.id,
            "step_order": approval.step_order,
            "step_name": step.step_name,
            "approver_user_id": approval.approver_user_id,
            "approver_name": approver.full_name or approver.email,
            "approver_email": approver.email,
            "status": approval.status,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
            "budget_code": approval.budget_code,
            "activity_code": approval.activity_code,
            "cost_center": approval.cost_center,
            "section": approval.section,
        })
    
    return result


@router.post("/{request_id}/submit")
async def submit_travel_request_with_workflow(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a travel request and initialize approval workflow"""
    travel_request = db.query(TravelRequest).filter(TravelRequest.id == request_id).first()
    if not travel_request:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    if travel_request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if travel_request.status.lower() not in ["draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Travel request cannot be submitted")
    
    # Get user's tenant
    tenant_id = travel_request.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Travel request has no tenant assigned")
    
    # Get active workflow for TRAVEL_REQUEST
    workflow = (
        db.query(ApprovalWorkflow)
        .filter(
            ApprovalWorkflow.tenant_id == str(tenant_id),
            ApprovalWorkflow.workflow_type == "TRAVEL_REQUEST",
            ApprovalWorkflow.is_active == True
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(status_code=400, detail="No active approval workflow found for travel requests")
    
    # Get workflow steps
    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.workflow_id == workflow.id)
        .order_by(ApprovalStep.step_order)
        .all()
    )
    
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow has no steps configured")
    
    # Delete existing approval records if resubmitting
    db.query(TravelRequestApprovalStep).filter(TravelRequestApprovalStep.travel_request_id == travel_request.id).delete()
    
    # Create approval records
    for step in steps:
        approval = TravelRequestApprovalStep(
            travel_request_id=travel_request.id,
            workflow_step_id=step.id,
            step_order=step.step_order,
            approver_user_id=step.approver_user_id,
            status="OPEN" if step.step_order == 1 else "PENDING"
        )
        db.add(approval)
    
    # Update travel request status and clear rejection data
    travel_request.status = "pending_approval"
    travel_request.submitted_at = datetime.utcnow()
    travel_request.rejection_reason = None
    travel_request.rejected_by = None
    travel_request.rejected_at = None
    travel_request.workflow_id = workflow.id
    travel_request.current_approval_step = 1
    
    db.commit()
    db.refresh(travel_request)
    
    return {"message": "Travel request submitted successfully", "status": travel_request.status}
