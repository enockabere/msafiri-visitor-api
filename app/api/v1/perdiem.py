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
from app.core.config import settings
from app.models.user import User
from app.services.email_service import send_email
from app.services.notification_service import create_notification

router = APIRouter()

@router.get("/test")
def test_endpoint():
    """Test endpoint to verify server is running latest code"""
    print("🔥 TEST ENDPOINT HIT - Server is running latest code!")
    return {"message": "Per diem API is working", "timestamp": datetime.utcnow().isoformat()}

@router.post("/", response_model=PerdiemRequestSchema)
def create_perdiem_request(
    request: PerdiemRequestCreate,
    participant_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print("="*80)
    print(f"🚨 ENDPOINT HIT - Per Diem Request Creation Started")
    print(f"🔧 DEBUG - Per Diem Request Data: {request.dict()}")
    print(f"🔧 DEBUG - Payment Method: {request.payment_method}")
    print(f"🔧 DEBUG - Cash Hours: {request.cash_hours}")
    print(f"🔧 DEBUG - PerdiemStatus.PENDING_APPROVAL enum: {PerdiemStatus.PENDING_APPROVAL}")
    print(f"🔧 DEBUG - PerdiemStatus.PENDING_APPROVAL.value: {PerdiemStatus.PENDING_APPROVAL.value}")
    print(f"🔧 DEBUG - About to create PerdiemRequest with status: {PerdiemStatus.PENDING_APPROVAL}")
    print(f"🔧 DEBUG - Participant ID: {participant_id}")
    print(f"🔧 DEBUG - Current User: {current_user.email if current_user else 'None'}")
    print("="*80)
    
    # Get participant and validate
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event details
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get daily rate from tenant's per diem setup
    from app.models.perdiem_setup import PerDiemSetup
    
    perdiem_setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == event.tenant_id
    ).first()
    
    if not perdiem_setup:
        raise HTTPException(status_code=400, detail="Per diem setup not configured for this tenant")
    
    daily_rate = perdiem_setup.daily_rate
    currency = perdiem_setup.currency
    total_amount = daily_rate * request.requested_days
    
    perdiem_request = PerdiemRequest(
        participant_id=participant_id,
        arrival_date=request.arrival_date,
        departure_date=request.departure_date,
        calculated_days=(request.departure_date - request.arrival_date).days + 1,
        requested_days=request.requested_days,
        daily_rate=daily_rate,
        currency=currency,
        total_amount=total_amount,
        status="pending_approval",  # Use string directly
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
        mpesa_number=request.mpesa_number,
        accommodation_type=request.accommodation_type,
        accommodation_name=request.accommodation_name
    )
    
    print(f"🔧 DEBUG - Created PerdiemRequest object with status: {perdiem_request.status}")
    print(f"🔧 DEBUG - Status type: {type(perdiem_request.status)}")
    print(f"🔧 DEBUG - Status repr: {repr(perdiem_request.status)}")
    print(f"🔧 DEBUG - About to add to database...")
    
    db.add(perdiem_request)
    
    print(f"🔧 DEBUG - About to commit to database...")
    db.commit()
    db.refresh(perdiem_request)
    
    print(f"🔧 DEBUG - Per diem request created successfully with ID: {perdiem_request.id}")
    print(f"🔧 DEBUG - Refreshed object: {perdiem_request.__dict__}")
    db.refresh(perdiem_request)
    
    # Send approval request emails
    background_tasks.add_task(
        send_perdiem_approval_emails,
        perdiem_request,
        participant,
        event,
        db
    )
    
    print(f"🔧 DEBUG - About to return per diem request: {perdiem_request}")
    print(f"🔧 DEBUG - Return data type: {type(perdiem_request)}")
    
    return perdiem_request

@router.get("/participant/{participant_id}", response_model=List[PerdiemRequestSchema])
def get_participant_perdiem_requests(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print("="*80)
    print(f"🔍 GET PERDIEM REQUESTS - Participant ID: {participant_id}")
    print(f"🔍 Current User: {current_user.email if current_user else 'None'}")
    
    requests = db.query(PerdiemRequest).filter(PerdiemRequest.participant_id == participant_id).all()
    
    print(f"🔍 Found {len(requests)} per diem requests for participant {participant_id}")
    
    # Add currency field to each request if not present
    for request in requests:
        if not hasattr(request, 'currency') or request.currency is None:
            request.currency = 'KES'  # Default currency
    
    if requests:
        for i, req in enumerate(requests):
            print(f"🔍 Request {i+1}: ID={req.id}, Status={req.status}, Currency={getattr(req, 'currency', 'KES')}, Created={req.created_at}")
    else:
        print(f"🔍 No requests found. Checking if participant exists...")
        participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
        if participant:
            print(f"🔍 Participant exists: {participant.first_name} {participant.last_name} ({participant.email})")
        else:
            print(f"🔍 Participant with ID {participant_id} does not exist!")
        
        # Check all per diem requests in database
        all_requests = db.query(PerdiemRequest).all()
        print(f"🔍 Total per diem requests in database: {len(all_requests)}")
        for req in all_requests:
            print(f"🔍   Request ID={req.id}, Participant={req.participant_id}, Status={req.status}")
    
    print("="*80)
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
        accommodation_type=perdiem_request.accommodation_type,
        accommodation_name=perdiem_request.accommodation_name,
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
        perdiem_request.status = PerdiemStatus.APPROVED
        perdiem_request.approved_at = current_time
        perdiem_request.approved_by = "Approver"  # Should get from token
    elif action.action == "reject":
        perdiem_request.status = PerdiemStatus.REJECTED
        perdiem_request.rejected_at = current_time
        perdiem_request.rejected_by = "Approver"  # Should get from token
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
    
    perdiem_request.status = PerdiemStatus.COMPLETED
    perdiem_request.payment_reference = payment.payment_reference
    if payment.admin_notes:
        perdiem_request.admin_notes = payment.admin_notes
    
    db.commit()
    db.refresh(perdiem_request)
    
    return {"message": "Payment recorded successfully"}

@router.post("/{request_id}/issue")
def issue_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if perdiem_request.status != PerdiemStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Can only issue approved requests")
    
    perdiem_request.status = PerdiemStatus.ISSUED
    db.commit()
    db.refresh(perdiem_request)
    
    return {"message": "Request issued successfully", "status": perdiem_request.status.value}

@router.put("/{request_id}", response_model=PerdiemRequestSchema)
def update_perdiem_request(
    request_id: int,
    request: PerdiemRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print("="*80)
    print(f"🔧 UPDATE PERDIEM REQUEST - ID: {request_id}")
    print(f"🔧 DEBUG - Update Data: {request.dict()}")
    print("="*80)
    
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Only allow updates for open requests
    if perdiem_request.status != "open":
        raise HTTPException(status_code=400, detail=f"Can only update open requests. Current status: {perdiem_request.status}")
    
    # Get participant and event to fetch tenant's per diem setup
    participant = db.query(EventParticipant).filter(EventParticipant.id == perdiem_request.participant_id).first()
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    # Get daily rate from tenant's per diem setup
    from app.models.perdiem_setup import PerDiemSetup
    
    perdiem_setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == event.tenant_id
    ).first()
    
    if not perdiem_setup:
        raise HTTPException(status_code=400, detail="Per diem setup not configured for this tenant")
    
    perdiem_request.daily_rate = perdiem_setup.daily_rate
    perdiem_request.currency = perdiem_setup.currency
    
    # Update fields
    perdiem_request.arrival_date = request.arrival_date
    perdiem_request.departure_date = request.departure_date
    perdiem_request.calculated_days = (request.departure_date - request.arrival_date).days + 1
    perdiem_request.requested_days = request.requested_days
    perdiem_request.justification = request.justification
    perdiem_request.event_type = request.event_type
    perdiem_request.purpose = request.purpose
    perdiem_request.approver_title = request.approver_title
    perdiem_request.approver_email = request.approver_email
    perdiem_request.phone_number = request.phone_number
    perdiem_request.email = request.email
    perdiem_request.payment_method = request.payment_method
    perdiem_request.cash_pickup_date = request.cash_pickup_date
    perdiem_request.cash_hours = request.cash_hours
    perdiem_request.mpesa_number = request.mpesa_number
    perdiem_request.accommodation_type = request.accommodation_type
    perdiem_request.accommodation_name = request.accommodation_name

    # Recalculate total amount
    perdiem_request.total_amount = perdiem_request.daily_rate * request.requested_days
    
    db.commit()
    db.refresh(perdiem_request)
    
    print(f"🔧 DEBUG - Per diem request updated successfully: {perdiem_request.id}")
    
    return perdiem_request

@router.delete("/{request_id}")
def delete_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    print(f"🔧 DEBUG - Delete request - Current status: {perdiem_request.status}")
    
    if perdiem_request.status not in ["open", "pending_approval"]:
        raise HTTPException(status_code=400, detail=f"Can only delete open or pending requests. Current status: {perdiem_request.status}")
    
    db.delete(perdiem_request)
    db.commit()
    
    print(f"🔧 DEBUG - Delete request - Request {request_id} deleted successfully")
    
    return {"message": "Request deleted successfully"}

@router.post("/{request_id}/cancel")
def cancel_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    print(f"🔧 DEBUG - Cancel request - Current status: {perdiem_request.status}")
    print(f"🔧 DEBUG - Cancel request - Status type: {type(perdiem_request.status)}")
    
    if perdiem_request.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Can only cancel pending requests. Current status: {perdiem_request.status}")
    
    perdiem_request.status = "open"
    db.commit()
    db.refresh(perdiem_request)
    
    print(f"🔧 DEBUG - Cancel request - New status: {perdiem_request.status}")
    
    return {"message": "Request cancelled successfully", "status": perdiem_request.status}

@router.post("/{request_id}/submit")
def submit_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    perdiem_request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not perdiem_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    print(f"🔧 DEBUG - Submit request - Current status: {perdiem_request.status}")
    print(f"🔧 DEBUG - Submit request - Status type: {type(perdiem_request.status)}")
    
    if perdiem_request.status != "open":
        raise HTTPException(status_code=400, detail=f"Can only submit open requests. Current status: {perdiem_request.status}")
    
    perdiem_request.status = "pending_approval"
    db.commit()
    db.refresh(perdiem_request)
    
    print(f"🔧 DEBUG - Submit request - New status: {perdiem_request.status}")
    
    return {"message": "Request submitted for approval", "status": perdiem_request.status}

@router.post("/{request_id}/received")
def mark_perdiem_received(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a per diem request as received by the participant"""
    
    # Get the request
    request = db.query(PerdiemRequest).filter(
        PerdiemRequest.id == request_id,
        PerdiemRequest.status == "issued"
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Issued request not found")
    
    # Get participant to verify ownership
    from app.models.event_participant import EventParticipant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == request.participant_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not authorized to mark this request as received")
    
    request.status = "completed"
    
    db.commit()
    db.refresh(request)
    
    return {"message": "Per diem marked as received successfully"}

def send_perdiem_approval_emails(request: PerdiemRequest, participant: EventParticipant, event: Event, db: Session):
    """Send email notifications for per diem approval request"""
    try:
        # Email to approver
        if request.approver_email:
            subject = f"Per Diem Approval Request - {event.title}"
            body = f"""
            <h2>Per Diem Approval Request</h2>
            <p>Dear {request.approver_title},</p>
            
            <p>A new per diem request has been submitted for your approval:</p>
            
            <ul>
                <li><strong>Participant:</strong> {participant.first_name} {participant.last_name}</li>
                <li><strong>Email:</strong> {participant.email}</li>
                <li><strong>Event:</strong> {event.title}</li>
                <li><strong>Event Location:</strong> {event.location or 'Not specified'}</li>
                <li><strong>Dates:</strong> {request.arrival_date} to {request.departure_date}</li>
                <li><strong>Days:</strong> {request.requested_days}</li>
                <li><strong>Purpose:</strong> {request.purpose}</li>
            </ul>
            
            <p>Please log in to the admin portal using Microsoft SSO to review and approve this request:</p>
            <p><a href="{settings.FRONTEND_URL}/per-diem-approvals">Login to Admin Portal to Approve</a></p>
            
            <p>Best regards,<br>MSafiri Team</p>
            """
            
            success = send_email(
                to_emails=[request.approver_email],
                subject=subject,
                body=body,
                is_html=True
            )
            
            if success:
                print(f"✅ Email sent successfully to approver: {request.approver_email}")
            else:
                print(f"❌ Failed to send email to approver: {request.approver_email}")
        
        # Email to requester (confirmation)
        confirmation_subject = f"Per Diem Request Submitted - {event.title}"
        confirmation_body = f"""
        <h2>Per Diem Request Confirmation</h2>
        <p>Dear {participant.first_name} {participant.last_name},</p>
        
        <p>Your per diem request has been submitted successfully:</p>
        
        <ul>
            <li><strong>Event:</strong> {event.title}</li>
            <li><strong>Event Location:</strong> {event.location or 'Not specified'}</li>
            <li><strong>Dates:</strong> {request.arrival_date} to {request.departure_date}</li>
            <li><strong>Days:</strong> {request.requested_days}</li>
            <li><strong>Approver:</strong> {request.approver_title} ({request.approver_email})</li>
        </ul>
        
        <p>Your request is now pending approval. You will be notified once it has been reviewed.</p>
        
        <p>Best regards,<br>MSafiri Team</p>
        """
        
        send_email(
            to_emails=[request.email],
            subject=confirmation_subject,
            body=confirmation_body,
            is_html=True
        )
        
    except Exception as e:
        print(f"❌ Error sending per diem approval emails: {e}")
