"""Tenant-specific travel advance endpoints for admin portal."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.models import TravelAdvance, TravelRequest, TravelRequestTraveler, User
from app.models.tenant import Tenant
from app.models.travel_advance import AdvanceStatus
from app.core.deps import get_current_user
from app.core.permissions import has_any_role

router = APIRouter()

REQUIRED_ROLES = ["FINANCE_ADMIN", "finance_admin", "SUPER_ADMIN", "super_admin"]


class ApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None


class DisburseAction(BaseModel):
    disbursement_reference: Optional[str] = None


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


def format_advance(advance: TravelAdvance, db: Session) -> dict:
    """Format a travel advance for response."""
    # Get the requester (user who created the advance request)
    requester = db.query(User).filter(User.id == advance.user_id).first()

    # Get the traveler info
    traveler = advance.traveler
    traveler_user = db.query(User).filter(User.id == traveler.user_id).first() if traveler and traveler.user_id else None

    # Get the travel request
    travel_request = advance.travel_request

    return {
        "id": advance.id,
        "travel_request_id": advance.travel_request_id,
        "traveler_id": advance.traveler_id,
        "user_id": advance.user_id,
        "tenant_id": advance.tenant_id,

        # Requester info
        "requester_name": requester.full_name or requester.email if requester else "Unknown",
        "requester_email": requester.email if requester else "Unknown",

        # Traveler info
        "traveler_name": traveler.traveler_name if traveler else "Unknown",
        "traveler_email": traveler_user.email if traveler_user else (traveler.traveler_email if traveler else None),
        "traveler_type": traveler.traveler_type.value if traveler and traveler.traveler_type else "employee",

        # Travel request info
        "travel_purpose": travel_request.purpose if travel_request else None,
        "destination_country": travel_request.destination_country if travel_request else None,
        "destination_city": travel_request.destination_city if travel_request else None,
        "departure_date": travel_request.departure_date.isoformat() if travel_request and travel_request.departure_date else None,
        "return_date": travel_request.return_date.isoformat() if travel_request and travel_request.return_date else None,

        # Advance details
        "expense_category": advance.expense_category.value if advance.expense_category else None,
        "amount": float(advance.amount) if advance.amount else 0,
        "currency": advance.currency,
        "status": advance.status.value if advance.status else "pending",

        # Per diem specific
        "accommodation_type": advance.accommodation_type.value if advance.accommodation_type else None,

        # Payment details
        "payment_method": advance.payment_method.value if advance.payment_method else "cash",
        "cash_pickup_date": advance.cash_pickup_date.isoformat() if advance.cash_pickup_date else None,
        "cash_hours": advance.cash_hours.value if advance.cash_hours else None,
        "mpesa_number": advance.mpesa_number,
        "bank_account": advance.bank_account,

        # Timestamps
        "created_at": advance.created_at.isoformat() if advance.created_at else None,
        "updated_at": advance.updated_at.isoformat() if advance.updated_at else None,

        # Approval tracking
        "approved_by": advance.approved_by,
        "approved_at": advance.approved_at.isoformat() if advance.approved_at else None,
        "rejected_by": advance.rejected_by,
        "rejected_at": advance.rejected_at.isoformat() if advance.rejected_at else None,
        "rejection_reason": advance.rejection_reason,

        # Disbursement tracking
        "disbursed_by": advance.disbursed_by,
        "disbursed_at": advance.disbursed_at.isoformat() if advance.disbursed_at else None,
        "disbursement_reference": advance.disbursement_reference,
    }


@router.get("/{tenant_slug}/travel-advances/pending")
async def get_pending_travel_advances(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get pending travel advances for a tenant."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advances = (
        db.query(TravelAdvance)
        .options(
            joinedload(TravelAdvance.traveler),
            joinedload(TravelAdvance.travel_request),
        )
        .filter(
            TravelAdvance.tenant_id == tenant.id,
            TravelAdvance.status == AdvanceStatus.PENDING
        )
        .order_by(TravelAdvance.created_at.desc())
        .all()
    )

    return [format_advance(adv, db) for adv in advances]


@router.get("/{tenant_slug}/travel-advances/approved")
async def get_approved_travel_advances(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approved travel advances for a tenant (ready for disbursement)."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advances = (
        db.query(TravelAdvance)
        .options(
            joinedload(TravelAdvance.traveler),
            joinedload(TravelAdvance.travel_request),
        )
        .filter(
            TravelAdvance.tenant_id == tenant.id,
            TravelAdvance.status == AdvanceStatus.APPROVED
        )
        .order_by(TravelAdvance.approved_at.desc())
        .all()
    )

    return [format_advance(adv, db) for adv in advances]


@router.get("/{tenant_slug}/travel-advances/disbursed")
async def get_disbursed_travel_advances(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get disbursed travel advances for a tenant."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advances = (
        db.query(TravelAdvance)
        .options(
            joinedload(TravelAdvance.traveler),
            joinedload(TravelAdvance.travel_request),
        )
        .filter(
            TravelAdvance.tenant_id == tenant.id,
            TravelAdvance.status == AdvanceStatus.DISBURSED
        )
        .order_by(TravelAdvance.disbursed_at.desc())
        .all()
    )

    return [format_advance(adv, db) for adv in advances]


@router.get("/{tenant_slug}/travel-advances/rejected")
async def get_rejected_travel_advances(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get rejected travel advances for a tenant."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advances = (
        db.query(TravelAdvance)
        .options(
            joinedload(TravelAdvance.traveler),
            joinedload(TravelAdvance.travel_request),
        )
        .filter(
            TravelAdvance.tenant_id == tenant.id,
            TravelAdvance.status == AdvanceStatus.REJECTED
        )
        .order_by(TravelAdvance.rejected_at.desc())
        .all()
    )

    return [format_advance(adv, db) for adv in advances]


@router.post("/{tenant_slug}/travel-advances/{advance_id}/approve")
async def approve_or_reject_travel_advance(
    tenant_slug: str,
    advance_id: int,
    action_data: ApprovalAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve or reject a travel advance."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advance = db.query(TravelAdvance).filter(
        TravelAdvance.id == advance_id,
        TravelAdvance.tenant_id == tenant.id
    ).first()

    if not advance:
        raise HTTPException(status_code=404, detail="Travel advance not found")

    if advance.status != AdvanceStatus.PENDING:
        raise HTTPException(status_code=400, detail="Advance is not in pending status")

    action = action_data.action.lower()

    if action == "approve":
        advance.status = AdvanceStatus.APPROVED
        advance.approved_by = current_user.id
        advance.approved_at = datetime.utcnow()
        message = "Travel advance approved successfully"
    elif action == "reject":
        if not action_data.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")

        advance.status = AdvanceStatus.REJECTED
        advance.rejected_by = current_user.id
        advance.rejected_at = datetime.utcnow()
        advance.rejection_reason = action_data.rejection_reason
        message = "Travel advance rejected successfully"
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve' or 'reject'")

    db.commit()
    return {"message": message}


@router.post("/{tenant_slug}/travel-advances/{advance_id}/disburse")
async def disburse_travel_advance(
    tenant_slug: str,
    advance_id: int,
    action_data: DisburseAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a travel advance as disbursed."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    advance = db.query(TravelAdvance).filter(
        TravelAdvance.id == advance_id,
        TravelAdvance.tenant_id == tenant.id
    ).first()

    if not advance:
        raise HTTPException(status_code=404, detail="Travel advance not found")

    if advance.status != AdvanceStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Advance must be approved before disbursement")

    advance.status = AdvanceStatus.DISBURSED
    advance.disbursed_by = current_user.id
    advance.disbursed_at = datetime.utcnow()
    advance.disbursement_reference = action_data.disbursement_reference

    db.commit()
    return {"message": "Travel advance disbursed successfully"}


@router.get("/{tenant_slug}/travel-advances/count")
async def get_travel_advance_count(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get count of pending travel advances for badge display."""
    tenant = get_tenant_or_404(db, tenant_slug)
    check_finance_access(current_user, db, tenant_slug)

    count = db.query(TravelAdvance).filter(
        TravelAdvance.tenant_id == tenant.id,
        TravelAdvance.status == AdvanceStatus.PENDING
    ).count()

    return {"count": count}
