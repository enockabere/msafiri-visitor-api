"""Travel advance endpoints."""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models import User, TravelAdvance, TravelRequest, TravelRequestTraveler, TravelRequestStatus
from app.schemas.travel_advance import TravelAdvanceCreate, TravelAdvanceResponse, TravelAdvanceUpdate

router = APIRouter()


@router.post("/", response_model=TravelAdvanceResponse, status_code=status.HTTP_201_CREATED)
def create_advance(
    advance_data: TravelAdvanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a travel advance request."""
    # Verify travel request exists and is approved
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == advance_data.travel_request_id
    ).first()
    
    if not travel_request:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    if travel_request.status != TravelRequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Travel request must be approved")
    
    # Verify traveler exists and belongs to this request
    traveler = db.query(TravelRequestTraveler).filter(
        TravelRequestTraveler.id == advance_data.traveler_id,
        TravelRequestTraveler.travel_request_id == advance_data.travel_request_id
    ).first()
    
    if not traveler:
        raise HTTPException(status_code=404, detail="Traveler not found")
    
    # Verify user is authorized (primary requester or the traveler themselves)
    if travel_request.user_id != current_user.id and traveler.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to request advance for this traveler")
    
    # Create advance
    advance = TravelAdvance(
        travel_request_id=advance_data.travel_request_id,
        traveler_id=advance_data.traveler_id,
        user_id=current_user.id,
        tenant_id=travel_request.tenant_id,
        expense_category=advance_data.expense_category,
        amount=advance_data.amount
    )
    
    db.add(advance)
    db.commit()
    db.refresh(advance)
    
    return advance


@router.get("/travel-request/{request_id}", response_model=List[TravelAdvanceResponse])
def get_advances_for_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all advances for a travel request."""
    # Verify travel request exists and user has access
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()
    
    if not travel_request:
        raise HTTPException(status_code=404, detail="Travel request not found")
    
    # Check if user is requester, traveler, or admin
    is_requester = travel_request.user_id == current_user.id
    is_traveler = db.query(TravelRequestTraveler).filter(
        TravelRequestTraveler.travel_request_id == request_id,
        TravelRequestTraveler.user_id == current_user.id
    ).first() is not None
    is_admin = any(ut.role == "admin" for ut in current_user.user_tenants if ut.tenant_id == travel_request.tenant_id)
    
    if not (is_requester or is_traveler or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view advances")
    
    advances = db.query(TravelAdvance).filter(
        TravelAdvance.travel_request_id == request_id
    ).order_by(TravelAdvance.created_at.desc()).all()
    
    return advances


@router.get("/my-advances", response_model=List[TravelAdvanceResponse])
def get_my_advances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all advances requested by current user."""
    advances = db.query(TravelAdvance).filter(
        TravelAdvance.user_id == current_user.id
    ).order_by(TravelAdvance.created_at.desc()).all()
    
    return advances


@router.put("/{advance_id}", response_model=TravelAdvanceResponse)
def update_advance_status(
    advance_id: int,
    update_data: TravelAdvanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update advance status (admin only)."""
    advance = db.query(TravelAdvance).filter(TravelAdvance.id == advance_id).first()
    
    if not advance:
        raise HTTPException(status_code=404, detail="Advance not found")
    
    # Verify user is admin
    is_admin = any(ut.role == "admin" for ut in current_user.user_tenants if ut.tenant_id == advance.tenant_id)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update advance status")
    
    # Update status
    advance.status = update_data.status
    
    if update_data.status == "approved":
        advance.approved_by = current_user.id
        advance.approved_at = datetime.utcnow()
    elif update_data.status == "rejected":
        advance.rejected_by = current_user.id
        advance.rejected_at = datetime.utcnow()
        advance.rejection_reason = update_data.rejection_reason
    elif update_data.status == "disbursed":
        advance.disbursed_by = current_user.id
        advance.disbursed_at = datetime.utcnow()
        advance.disbursement_reference = update_data.disbursement_reference
    
    db.commit()
    db.refresh(advance)
    
    return advance
