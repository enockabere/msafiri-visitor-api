from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.cash_claim import Claim
from app.models.claim_approval import ClaimApproval
from app.models.approver import ApprovalWorkflow, ApprovalStep
from app.models.user import User
from app.core.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("/{claim_id}/approvals")
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


@router.post("/{claim_id}/submit")
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
    
    if claim.status.lower() not in ["draft", "open"]:
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
        db.query(ApprovalStep)
        .filter(ApprovalStep.workflow_id == workflow.id)
        .order_by(ApprovalStep.step_order)
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
    db.refresh(claim)
    
    # Return the updated claim in the format expected by mobile app
    return {
        "id": claim.id,
        "user_id": claim.user_id,
        "description": claim.description,
        "total_amount": float(claim.total_amount),
        "currency": claim.currency,
        "status": claim.status,
        "expense_type": claim.expense_type,
        "payment_method": claim.payment_method,
        "mpesa_number": claim.mpesa_number,
        "bank_account": claim.bank_account,
        "cash_pickup_date": claim.cash_pickup_date.isoformat() if claim.cash_pickup_date else None,
        "cash_hours": claim.cash_hours,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None,
        "approved_at": claim.approved_at.isoformat() if claim.approved_at else None,
        "approved_by": claim.approved_by,
        "items": []
    }
