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
    
    if action == "approve":
        request.status = "approved"
        request.approved_by = current_user.email
        request.approved_at = datetime.utcnow()
        
    elif action == "reject":
        request.status = "rejected"
        request.rejected_by = current_user.email
        request.rejected_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    return {"message": f"Request {action}d successfully"}