from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.cash_claim import Claim, ClaimItem
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.cash_claim import ClaimApprovalAction
from app.core.deps import get_current_user
from app.core.permissions import has_any_role
from datetime import datetime

router = APIRouter()

REQUIRED_ROLES = ["FINANCE_ADMIN", "finance_admin", "SUPER_ADMIN", "super_admin"]


def get_tenant_or_404(db: Session, tenant_slug: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def check_finance_access(user: User, db: Session, tenant_slug: str):
    """Check FINANCE_ADMIN or SUPER_ADMIN role across all role sources."""
    # Check via has_any_role (primary role + user_roles table)
    if has_any_role(user, db, REQUIRED_ROLES):
        return

    # Also check UserTenant roles for this specific tenant
    from app.models.user_tenants import UserTenant, UserTenantRole
    tenant_role = db.query(UserTenant).filter(
        UserTenant.user_id == user.id,
        UserTenant.tenant_id == tenant_slug,
        UserTenant.is_active == True,
        UserTenant.role.in_([UserTenantRole.FINANCE_ADMIN, UserTenantRole.SUPER_ADMIN]),
    ).first()

    if tenant_role:
        return

    raise HTTPException(status_code=403, detail="Finance Admin or Super Admin role required")


def format_claim(claim: Claim, submitter: User) -> dict:
    items = []
    for item in claim.items:
        items.append({
            "id": item.id,
            "merchant_name": item.merchant_name,
            "amount": float(item.amount) if item.amount else 0,
            "date": item.date.isoformat() if item.date else None,
            "category": item.category,
            "receipt_image_url": item.receipt_image_url,
            "extracted_data": item.extracted_data,
        })

    return {
        "id": claim.id,
        "user_id": claim.user_id,
        "submitter_name": submitter.full_name or submitter.email if submitter else "Unknown",
        "submitter_email": submitter.email if submitter else "Unknown",
        "description": claim.description,
        "total_amount": float(claim.total_amount) if claim.total_amount else 0,
        "expense_type": claim.expense_type,
        "payment_method": claim.payment_method,
        "cash_pickup_date": claim.cash_pickup_date.isoformat() if claim.cash_pickup_date else None,
        "cash_hours": claim.cash_hours,
        "mpesa_number": claim.mpesa_number,
        "bank_account": claim.bank_account,
        "status": claim.status,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None,
        "approved_at": claim.approved_at.isoformat() if claim.approved_at else None,
        "approved_by": claim.approved_by,
        "rejection_reason": claim.rejection_reason,
        "rejected_by": claim.rejected_by,
        "rejected_at": claim.rejected_at.isoformat() if claim.rejected_at else None,
        "items": items,
    }


@router.get("/{tenant_slug}/expense-claims/pending")
async def get_pending_expense_claims(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get pending expense claims for a tenant.

    Includes claims with status 'Pending Approval', 'submitted', and 'Open'
    (Open claims that have items are likely ready for review).
    """
    get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    claims = (
        db.query(Claim, User)
        .join(User, Claim.user_id == User.id)
        .filter(Claim.status.in_(["Pending Approval", "submitted", "Open"]))
        .order_by(Claim.submitted_at.desc().nullslast(), Claim.created_at.desc())
        .all()
    )

    return [format_claim(claim, submitter) for claim, submitter in claims]


@router.get("/{tenant_slug}/expense-claims/approved")
async def get_approved_expense_claims(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approved expense claims for a tenant"""
    get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    claims = (
        db.query(Claim, User)
        .join(User, Claim.user_id == User.id)
        .filter(Claim.status == "Approved")
        .order_by(Claim.approved_at.desc())
        .all()
    )

    return [format_claim(claim, submitter) for claim, submitter in claims]


@router.get("/{tenant_slug}/expense-claims/rejected")
async def get_rejected_expense_claims(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get rejected expense claims for a tenant"""
    get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    claims = (
        db.query(Claim, User)
        .join(User, Claim.user_id == User.id)
        .filter(Claim.status == "Rejected")
        .order_by(Claim.rejected_at.desc())
        .all()
    )

    return [format_claim(claim, submitter) for claim, submitter in claims]


@router.post("/{tenant_slug}/expense-claims/{claim_id}/approve")
async def approve_or_reject_expense_claim(
    tenant_slug: str,
    claim_id: int,
    action_data: ClaimApprovalAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve or reject an expense claim"""
    from app.models.claim_approval import ClaimApproval
    
    get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status not in ("Pending Approval", "submitted", "Open"):
        raise HTTPException(status_code=400, detail="Claim is not in a pending status")

    action = action_data.action

    if action == "approve":
        # Find the current user's OPEN approval step
        current_approval = db.query(ClaimApproval).filter(
            ClaimApproval.claim_id == claim_id,
            ClaimApproval.approver_user_id == current_user.id,
            ClaimApproval.status == "OPEN"
        ).first()
        
        if not current_approval:
            raise HTTPException(status_code=403, detail="You are not authorized to approve this claim at this step")
        
        # Mark current step as APPROVED
        current_approval.status = "APPROVED"
        current_approval.approved_at = datetime.utcnow()
        
        # Check if there are more steps
        next_approval = db.query(ClaimApproval).filter(
            ClaimApproval.claim_id == claim_id,
            ClaimApproval.step_order > current_approval.step_order
        ).order_by(ClaimApproval.step_order).first()
        
        if next_approval:
            # Move next step to OPEN
            next_approval.status = "OPEN"
        else:
            # All steps completed - approve the claim
            claim.status = "Approved"
            claim.approved_by = current_user.id
            claim.approved_at = datetime.utcnow()
            
    elif action == "reject":
        if not action_data.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        # Find the current user's OPEN approval step
        current_approval = db.query(ClaimApproval).filter(
            ClaimApproval.claim_id == claim_id,
            ClaimApproval.approver_user_id == current_user.id,
            ClaimApproval.status == "OPEN"
        ).first()
        
        if not current_approval:
            raise HTTPException(status_code=403, detail="You are not authorized to reject this claim at this step")
        
        # Mark current step as REJECTED
        current_approval.status = "REJECTED"
        current_approval.rejected_at = datetime.utcnow()
        current_approval.rejection_reason = action_data.rejection_reason
        
        # Reject the entire claim
        claim.status = "Rejected"
        claim.rejected_by = current_user.id
        claim.rejected_at = datetime.utcnow()
        claim.rejection_reason = action_data.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve' or 'reject'")

    db.commit()
    return {"message": f"Claim {action}d successfully"}
