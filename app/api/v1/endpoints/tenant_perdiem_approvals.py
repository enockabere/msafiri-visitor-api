from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event import Event
from app.models.tenant import Tenant
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.schemas.perdiem_request import PerdiemApprovalAction
from app.core.deps import get_current_user
from datetime import datetime
from typing import List

router = APIRouter()

@router.get("/{tenant_slug}/per-diem-approvals/pending")
async def get_tenant_pending_approvals(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending per diem requests for a specific tenant"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get pending requests for this tenant where current user is the approver
    requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        Event.tenant_id == tenant.id,
        PerdiemRequest.approver_email == current_user.email,
        PerdiemRequest.status == "pending_approval"
    ).all()
    
    # Format response to match frontend expectations
    result = []
    for request in requests:
        participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
        event = db.query(Event).filter(Event.id == participant.event_id).first() if participant else None
        
        if participant and event:
            result.append({
                "id": request.id,
                "participant_name": participant.full_name or participant.email,
                "participant_email": participant.email,
                "event_name": event.title,
                "event_dates": f"{event.start_date} to {event.end_date}",
                "arrival_date": str(request.arrival_date),
                "departure_date": str(request.departure_date),
                "requested_days": request.requested_days,
                "daily_rate": float(request.daily_rate),
                "total_amount": float(request.total_amount),
                "purpose": request.purpose or request.justification or "Event participation",
                "approver_title": request.approver_title or "Per Diem Approver",
                "phone_number": request.phone_number or participant.phone_number or "",
                "payment_method": request.payment_method.value if request.payment_method else "CASH",
                "status": request.status,
                "created_at": request.created_at.isoformat() if request.created_at else None
            })
    
    return result

@router.get("/{tenant_slug}/per-diem-approvals/approved")
async def get_tenant_approved_requests(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get approved per diem requests for a specific tenant"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get approved requests for this tenant
    requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        Event.tenant_id == tenant.id,
        PerdiemRequest.status == "approved"
    ).all()
    
    # Format response to match frontend expectations
    result = []
    for request in requests:
        participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
        event = db.query(Event).filter(Event.id == participant.event_id).first() if participant else None
        
        if participant and event:
            result.append({
                "id": request.id,
                "participant_name": participant.full_name or participant.email,
                "participant_email": participant.email,
                "event_name": event.title,
                "event_dates": f"{event.start_date} to {event.end_date}",
                "arrival_date": str(request.arrival_date),
                "departure_date": str(request.departure_date),
                "requested_days": request.requested_days,
                "daily_rate": float(request.daily_rate),
                "total_amount": float(request.total_amount),
                "purpose": request.purpose or request.justification or "Event participation",
                "approver_title": request.approver_title or "Per Diem Approver",
                "phone_number": request.phone_number or participant.phone_number or "",
                "payment_method": request.payment_method.value if request.payment_method else "CASH",
                "status": request.status,
                "created_at": request.created_at.isoformat() if request.created_at else None,
                "approved_by": request.approved_by,
                "approved_at": request.approved_at.isoformat() if request.approved_at else None
            })
    
    return result

@router.get("/{tenant_slug}/per-diem-approvals/issued")
async def get_tenant_issued_requests(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get issued per diem requests for a specific tenant"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get issued requests for this tenant
    requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        Event.tenant_id == tenant.id,
        PerdiemRequest.status == "issued"
    ).all()
    
    # Format response to match frontend expectations
    result = []
    for request in requests:
        participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
        event = db.query(Event).filter(Event.id == participant.event_id).first() if participant else None
        
        if participant and event:
            result.append({
                "id": request.id,
                "participant_name": participant.full_name or participant.email,
                "participant_email": participant.email,
                "event_name": event.title,
                "event_dates": f"{event.start_date} to {event.end_date}",
                "arrival_date": str(request.arrival_date),
                "departure_date": str(request.departure_date),
                "requested_days": request.requested_days,
                "daily_rate": float(request.daily_rate),
                "total_amount": float(request.total_amount),
                "purpose": request.purpose or request.justification or "Event participation",
                "approver_title": request.approver_title or "Per Diem Approver",
                "phone_number": request.phone_number or participant.phone_number or "",
                "payment_method": request.payment_method.value if request.payment_method else "CASH",
                "status": request.status,
                "created_at": request.created_at.isoformat() if request.created_at else None,
                "approved_by": request.approved_by,
                "approved_at": request.approved_at.isoformat() if request.approved_at else None
            })
    
    return result

@router.get("/{tenant_slug}/per-diem-approvals/rejected")
async def get_tenant_rejected_requests(
    tenant_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rejected per diem requests for a specific tenant"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get rejected requests for this tenant
    requests = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        Event.tenant_id == tenant.id,
        PerdiemRequest.status == "rejected"
    ).all()
    
    # Format response to match frontend expectations
    result = []
    for request in requests:
        participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
        event = db.query(Event).filter(Event.id == participant.event_id).first() if participant else None
        
        if participant and event:
            result.append({
                "id": request.id,
                "participant_name": participant.full_name or participant.email,
                "participant_email": participant.email,
                "event_name": event.title,
                "event_dates": f"{event.start_date} to {event.end_date}",
                "arrival_date": str(request.arrival_date),
                "departure_date": str(request.departure_date),
                "requested_days": request.requested_days,
                "daily_rate": float(request.daily_rate),
                "total_amount": float(request.total_amount),
                "purpose": request.purpose or request.justification or "Event participation",
                "approver_title": request.approver_title or "Per Diem Approver",
                "phone_number": request.phone_number or participant.phone_number or "",
                "payment_method": request.payment_method.value if request.payment_method else "CASH",
                "status": request.status,
                "created_at": request.created_at.isoformat() if request.created_at else None,
                "rejected_by": request.rejected_by,
                "rejected_at": request.rejected_at.isoformat() if request.rejected_at else None,
                "rejection_reason": request.rejection_reason
            })
    
    return result

@router.post("/{tenant_slug}/per-diem-approvals/{request_id}/approve")
async def approve_tenant_perdiem(
    tenant_slug: str,
    request_id: int,
    action_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject a per diem request for a specific tenant"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get the request
    request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        PerdiemRequest.id == request_id,
        Event.tenant_id == tenant.id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.approver_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to approve this request")
    
    action = action_data.get("action")
    rejection_reason = action_data.get("rejection_reason")
    approval_data = action_data.get("approval_data")
    
    if action == "approve":
        request.status = "approved"
        request.approved_by = current_user.email
        request.approved_at = datetime.utcnow()
        
        # Store approval data if provided
        if approval_data:
            request.approver_role = approval_data.get("role")
            request.approver_full_name = approval_data.get("fullName")
            request.budget_code = approval_data.get("budgetCode")
            request.activity_code = approval_data.get("activityCode")
            request.cost_center = approval_data.get("costCenter")
            request.section = approval_data.get("section")
        
    elif action == "reject":
        request.status = "rejected"
        request.rejected_by = current_user.email
        request.rejected_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    return {"message": f"Request {action}d successfully"}

@router.post("/{tenant_slug}/per-diem-approvals/{request_id}/issue")
async def issue_tenant_perdiem(
    tenant_slug: str,
    request_id: int,
    issue_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Issue an approved per diem request (Finance Admin only)"""
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if user has finance admin role
    user_roles = []
    if hasattr(current_user, 'all_roles') and current_user.all_roles:
        user_roles = current_user.all_roles
    elif current_user.role:
        user_roles = [current_user.role]
    
    has_finance_access = any(role.upper() in ['FINANCE_ADMIN', 'SUPER_ADMIN'] for role in user_roles)
    if not has_finance_access:
        raise HTTPException(status_code=403, detail="Only Finance Admin can issue per diem payments")
    
    # Get the request
    request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        PerdiemRequest.id == request_id,
        Event.tenant_id == tenant.id,
        PerdiemRequest.status == "approved"
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Approved request not found")
    
    # Update with daily rate, currency and calculate total
    daily_rate = issue_data.get("daily_rate")
    currency = issue_data.get("currency", "USD")
    
    if not daily_rate:
        raise HTTPException(status_code=400, detail="Daily rate is required")
    
    request.daily_rate = daily_rate
    request.currency = currency
    request.total_amount = daily_rate * request.requested_days
    request.status = "issued"
    
    db.commit()
    return {"message": "Per diem issued successfully"}