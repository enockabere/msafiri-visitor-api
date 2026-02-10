from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.cash_claim import Claim
from app.models.claim_approval import ClaimApproval
from app.models.approval_workflow import ApprovalWorkflow, ApprovalWorkflowStep
from app.models.user import User
from app.core.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("/claims/{claim_id}/approvals")
async def get_claim_approvals(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approval status for a claim"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check if user owns the claim
    if claim.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this claim")
    
    # Get all approvals for this claim
    approvals = (
        db.query(ClaimApproval, User)
        .join(User, ClaimApproval.approver_user_id == User.id)
        .filter(ClaimApproval.claim_id == claim_id)
        .order_by(ClaimApproval.step_order)
        .all()
    )
    
    result = []
    for approval, approver in approvals:
        result.append({
            "id": approval.id,
            "step_order": approval.step_order,
            "approver_name": approver.full_name or approver.email,
            "approver_email": approver.email,
            "status": approval.status,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
            "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
            "rejection_reason": approval.rejection_reason,
        })
    
    return result


@router.post("/claims/{claim_id}/submit")
async def submit_claim_with_workflow(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a claim and initialize approval workflow"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if claim.status != "draft":
        raise HTTPException(status_code=400, detail="Claim already submitted")
    
    # Get user's tenant
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")
    
    # Get active workflow for EXPENSE_CLAIM
    workflow = (
        db.query(ApprovalWorkflow)
        .filter(
            ApprovalWorkflow.tenant_id == tenant_id,
            ApprovalWorkflow.workflow_type == "EXPENSE_CLAIM",
            ApprovalWorkflow.is_active == True
        )
        .first()
    )
    
    if not workflow:
        raise HTTPException(status_code=400, detail="No active approval workflow found for expense claims")
    
    # Get workflow steps
    steps = (
        db.query(ApprovalWorkflowStep)
        .filter(ApprovalWorkflowStep.workflow_id == workflow.id)
        .order_by(ApprovalWorkflowStep.step_order)
        .all()
    )
    
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow has no steps configured")
    
    # Create approval records
    for step in steps:
        approval = ClaimApproval(
            claim_id=claim.id,
            workflow_step_id=step.id,
            step_order=step.step_order,
            approver_user_id=step.approver_user_id,
            status="OPEN" if step.step_order == 1 else "PENDING"
        )
        db.add(approval)
    
    # Update claim status
    claim.status = "Pending Approval"
    claim.submitted_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Claim submitted successfully", "workflow_steps": len(steps)}
