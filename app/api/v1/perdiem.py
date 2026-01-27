from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.tenant import Tenant
from app.models.user import User as UserModel
from app.schemas.perdiem_request import (
    PerdiemRequestCreate, 
    PerdiemRequest as PerdiemRequestSchema,
    PerdiemApprovalAction,
    PerdiemPaymentAction,
    PerdiemPublicView
)
from app.core.deps import get_current_user
from app.models.user import User
from app.services.email_service import send_email
from app.services.notification_service import create_notification

router = APIRouter()

@router.post("/", response_model=PerdiemRequestSchema)
def create_perdiem_request(
    request: PerdiemRequestCreate,
    participant_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"🔧 DEBUG - Per Diem Request Data: {request.dict()}")
    print(f"🔧 DEBUG - Payment Method: {request.payment_method}")
    print(f"🔧 DEBUG - Cash Hours: {request.cash_hours}")
    
    # Get participant and validate
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event details
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Calculate daily rate and total amount (simplified - should be based on event/location)
    daily_rate = 50.00  # Default rate
    total_amount = daily_rate * request.requested_days
    
    perdiem_request = PerdiemRequest(
        participant_id=participant_id,
        arrival_date=request.arrival_date,
        departure_date=request.departure_date,
        calculated_days=(request.departure_date - request.arrival_date).days + 1,
        requested_days=request.requested_days,
        daily_rate=daily_rate,
        total_amount=total_amount,
        justification=request.justification,
        event_type=request.event_type,
        purpose=request.purpose,
        approver_title=request.approver_title,
        approver_email=request.approver_email,
        phone_number=request.phone_number,
        email=request.email,
        payment_method=request.payment_method,
        cash_pickup_date=request.cash_pickup_date,
        cash_hours=request.cash_hours,
        mpesa_number=request.mpesa_number
    )
    
    db.add(perdiem_request)
    db.commit()
    db.refresh(perdiem_request)
    
    # Send approval request emails
    background_tasks.add_task(
        send_perdiem_approval_emails,
        perdiem_request,
        participant,
        event,
        db
    )
    
    return perdiem_request

@router.get("/participant/{participant_id}", response_model=List[PerdiemRequestSchema])
def get_participant_perdiem_requests(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    requests = db.query(PerdiemRequest).filter(PerdiemRequest.participant_id == participant_id).all()
    return requests

@router.get("/public/{request_id}/{token}")
def get_public_perdiem_request(
    request_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    # Validate token (simplified - should use proper JWT validation)
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    participant = db.query(EventParticipant).filter(EventParticipant.id == perdiem_request.participant_id).first()
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    return PerdiemPublicView(
        id=perdiem_request.id,
        participant_name=f"{participant.first_name} {participant.last_name}",
        participant_email=participant.email,
        event_name=event.title,
        event_dates=f"{event.start_date} to {event.end_date}",
        arrival_date=perdiem_request.arrival_date,
        departure_date=perdiem_request.departure_date,
        requested_days=perdiem_request.requested_days,
        daily_rate=perdiem_request.daily_rate,
        total_amount=perdiem_request.total_amount,
        justification=perdiem_request.justification,
        phone_number=perdiem_request.phone_number,
        payment_method=perdiem_request.payment_method,
        cash_pickup_date=perdiem_request.cash_pickup_date,
        cash_hours=perdiem_request.cash_hours,
        mpesa_number=perdiem_request.mpesa_number,
        status=perdiem_request.status.value,
        created_at=perdiem_request.created_at
    )

@router.post("/public/{request_id}/{token}/approve")
def approve_perdiem_request(
    request_id: int,
    token: str,
    action: PerdiemApprovalAction,
    db: Session = Depends(get_db)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    current_time = datetime.utcnow()
    
    if action.action == "approve":
        if perdiem_request.status == PerdiemStatus.PENDING:
            perdiem_request.status = PerdiemStatus.LINE_MANAGER_APPROVED
            perdiem_request.line_manager_approved_at = current_time
            perdiem_request.line_manager_approved_by = "Line Manager"  # Should get from token
        elif perdiem_request.status == PerdiemStatus.LINE_MANAGER_APPROVED:
            perdiem_request.status = PerdiemStatus.BUDGET_OWNER_APPROVED
            perdiem_request.budget_owner_approved_at = current_time
            perdiem_request.budget_owner_approved_by = "Budget Owner"  # Should get from token
    elif action.action == "reject":
        perdiem_request.status = PerdiemStatus.REJECTED
        perdiem_request.rejected_at = current_time
        perdiem_request.rejected_by = "Manager"  # Should get from token
        perdiem_request.rejection_reason = action.rejection_reason
    
    perdiem_request.admin_notes = action.notes
    
    db.commit()
    db.refresh(perdiem_request)
    
    return {"message": f"Request {action.action}d successfully", "status": perdiem_request.status.value}

@router.post("/{request_id}/payment")
def mark_as_paid(
    request_id: int,
    payment: PerdiemPaymentAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    perdiem_request.status = PerdiemStatus.PAID
    perdiem_request.payment_reference = payment.payment_reference
    if payment.admin_notes:
        perdiem_request.admin_notes = payment.admin_notes
    
    db.commit()
    db.refresh(perdiem_request)
    
    return {"message": "Payment recorded successfully"}

@router.get("/", response_model=List[PerdiemRequestSchema])
def get_all_perdiem_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    requests = db.query(PerdiemRequest).all()
    return requests

async def send_perdiem_approval_emails(request: PerdiemRequest, participant: EventParticipant, event: Event, db: Session):
    """Send email notifications for per diem approval request"""
    try:
        # Get tenant and finance admins
        tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first()
        finance_admins = db.query(UserModel).filter(
            UserModel.role.in_(["FINANCE_ADMIN", "finance_admin"])
        ).all()
        
        # Email to approver
        if request.approver_email:
            await send_email(
                to_email=request.approver_email,
                subject=f"Per Diem Approval Request - {event.title}",
                template="perdiem_approval_request",
                context={
                    "request": request,
                    "participant": participant,
                    "event": event,
                    "is_approver": True
                }
            )
        
        # Email to requester (confirmation)
        await send_email(
            to_email=request.email,
            subject=f"Per Diem Request Submitted - {event.title}",
            template="perdiem_request_confirmation",
            context={
                "request": request,
                "participant": participant,
                "event": event
            }
        )
        
        # Email to finance admins (CC)
        for admin in finance_admins:
            await send_email(
                to_email=admin.email,
                subject=f"Per Diem Request Submitted - {event.title}",
                template="perdiem_approval_request",
                context={
                    "request": request,
                    "participant": participant,
                    "event": event,
                    "is_admin": True
                }
            )
            
            # Create notification for admin
            await create_notification(
                user_id=admin.id,
                title="New Per Diem Request",
                message=f"Per diem request submitted for {event.title}",
                type="perdiem_request",
                tenant_id=tenant.id if tenant else None
            )
            
    except Exception as e:
        print(f"Error sending per diem approval emails: {e}")