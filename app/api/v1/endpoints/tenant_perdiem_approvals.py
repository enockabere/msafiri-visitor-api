from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event import Event
from app.models.tenant import Tenant
from app.models.perdiem_setup import PerDiemSetup
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
                "approved_by_name": request.approver_full_name,
                "approved_by_email": request.approved_by,
                "approved_at": request.approved_at.isoformat() if request.approved_at else None,
                "budget_code": request.budget_code,
                "activity_code": request.activity_code,
                "cost_center": request.cost_center,
                "section": request.section,
                "approver_role": request.approver_role
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
                "rejected_by_name": request.approver_full_name,
                "rejected_by_email": request.rejected_by,
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
    
    # Get participant and event details for email
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    event = db.query(Event).filter(Event.id == participant.event_id).first() if participant else None
    
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
        
        # Get per-diem setup for amount calculation
        setup = db.query(PerDiemSetup).filter(PerDiemSetup.tenant_id == tenant.id).first()
        daily_rate = float(setup.daily_rate) if setup else 0
        currency = setup.currency if setup else "USD"
        total_amount = daily_rate * request.requested_days
        
        # Send email to Finance Admin
        if participant and event:
            background_tasks.add_task(
                send_perdiem_approved_email,
                tenant_slug=tenant_slug,
                participant_name=participant.full_name or participant.email,
                participant_email=participant.email,
                event_name=event.title,
                event_location=getattr(event, 'location', 'TBD'),
                event_dates=f"{event.start_date} to {event.end_date}",
                requested_days=request.requested_days,
                daily_rate=daily_rate,
                currency=currency,
                total_amount=total_amount,
                purpose=request.purpose or request.justification or "Event participation",
                approver_name=approval_data.get("fullName") if approval_data else current_user.email,
                approver_email=current_user.email,
                approver_role=approval_data.get("role", "Per Diem Approver") if approval_data else "Per Diem Approver",
                budget_code=approval_data.get("budgetCode") if approval_data else "",
                activity_code=approval_data.get("activityCode") if approval_data else "",
                cost_center=approval_data.get("costCenter") if approval_data else "",
                section=approval_data.get("section") if approval_data else ""
            )
        
    elif action == "reject":
        request.status = "rejected"
        request.rejected_by = current_user.email
        request.rejected_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
        
        # Send rejection email to participant
        if participant and event:
            background_tasks.add_task(
                send_perdiem_rejected_email,
                participant_name=participant.full_name or participant.email,
                participant_email=participant.email,
                event_name=event.title,
                event_location=getattr(event, 'location', 'TBD'),
                event_dates=f"{event.start_date} to {event.end_date}",
                requested_days=request.requested_days,
                purpose=request.purpose or request.justification or "Event participation",
                rejection_reason=rejection_reason,
                rejected_by=current_user.email
            )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    return {"message": f"Request {action}d successfully"}


async def send_perdiem_approved_email(
    tenant_slug: str,
    participant_name: str,
    participant_email: str,
    event_name: str,
    event_location: str,
    event_dates: str,
    requested_days: int,
    daily_rate: float,
    currency: str,
    total_amount: float,
    purpose: str,
    approver_name: str,
    approver_email: str,
    approver_role: str,
    budget_code: str,
    activity_code: str,
    cost_center: str,
    section: str
):
    """Send email notification to Finance Admin when per diem is approved"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.core.email import send_email
        
        logger.info(f"Starting to send per diem approved email for participant: {participant_email}")
        
        # Get Finance Admin emails (you may need to adjust this query based on your user model)
        # For now, using a placeholder - you should implement proper Finance Admin lookup
        finance_admin_emails = ["finance@msf.org"]  # Replace with actual Finance Admin lookup
        
        logger.info(f"Finance admin emails: {finance_admin_emails}")
        
        subject = "Per Diem Payment Authorization Required"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #d32f2f;">Per Diem Payment Authorization Required</h2>
            
            <p>Dear Finance Admin,</p>
            
            <p>A per diem request has been approved and requires payment authorization:</p>
            
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #333;">Request Details</h3>
                <p><strong>Participant:</strong> {participant_name}</p>
                <p><strong>Email:</strong> {participant_email}</p>
                <p><strong>Event:</strong> {event_name}</p>
                <p><strong>Event Location:</strong> {event_location}</p>
                <p><strong>Dates:</strong> {event_dates}</p>
                <p><strong>Days:</strong> {requested_days}</p>
                <p><strong>Daily Rate:</strong> {currency} {daily_rate:,.2f}</p>
                <p><strong>Total Amount:</strong> {currency} {total_amount:,.2f}</p>
                <p><strong>Purpose:</strong> {purpose}</p>
            </div>
            
            <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2e7d32;">Approval Details</h3>
                <p><strong>Approved by:</strong> {approver_name}</p>
                <p><strong>Approver Email:</strong> {approver_email}</p>
                <p><strong>Confirmed Role:</strong> {approver_role}</p>
                <p><strong>Budget Code:</strong> {budget_code}</p>
                <p><strong>Activity Code:</strong> {activity_code}</p>
                <p><strong>Cost Center:</strong> {cost_center}</p>
                <p><strong>Section:</strong> {section}</p>
            </div>
            
            <p>Please log in to the admin portal to issue the payment:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://admin.msafiri.com/tenant/{tenant_slug}/per-diem-approvals" 
                   style="background-color: #d32f2f; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Login to Admin Portal to Issue Payment
                </a>
            </div>
            
            <p><em>Note: Use your Microsoft SSO credentials to login. You will need Finance Admin role to issue payments.</em></p>
            
            <p>Best regards,<br>MSafiri Team</p>
        </div>
        """
        
        # Send to Finance Admin, CC participant and approver
        for finance_email in finance_admin_emails:
            logger.info(f"Sending email to finance admin: {finance_email}, CC: {[participant_email, approver_email]}")
            await send_email(
                to_email=finance_email,
                cc_emails=[participant_email, approver_email],
                subject=subject,
                html_content=html_content
            )
            logger.info(f"Email sent successfully to {finance_email}")
            
    except Exception as e:
        logger.error(f"Failed to send per diem approved email: {e}", exc_info=True)
        print(f"Failed to send per diem approved email: {e}")
            
async def send_perdiem_rejected_email(
    participant_name: str,
    participant_email: str,
    event_name: str,
    event_location: str,
    event_dates: str,
    requested_days: int,
    purpose: str,
    rejection_reason: str,
    rejected_by: str
):
    """Send email notification to participant when per diem is rejected"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.core.email import send_email
        
        logger.info(f"Starting to send per diem rejection email to participant: {participant_email}")
        
        subject = "Per Diem Request Rejected"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #d32f2f;">Per Diem Request Rejected</h2>
            
            <p>Dear {participant_name},</p>
            
            <p>Unfortunately, your per diem request has been rejected:</p>
            
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #333;">Request Details</h3>
                <p><strong>Event:</strong> {event_name}</p>
                <p><strong>Event Location:</strong> {event_location}</p>
                <p><strong>Dates:</strong> {event_dates}</p>
                <p><strong>Days:</strong> {requested_days}</p>
                <p><strong>Purpose:</strong> {purpose}</p>
            </div>
            
            <div style="background-color: #ffebee; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d32f2f;">
                <h3 style="margin-top: 0; color: #d32f2f;">Reason for Rejection</h3>
                <p style="font-style: italic; color: #666;">"{rejection_reason}"</p>
                <p><strong>Rejected by:</strong> {rejected_by}</p>
            </div>
            
            <p>If you have any questions about this decision or would like to discuss the rejection, please contact the approver directly.</p>
            
            <p>You may submit a new per diem request if the issues mentioned in the rejection reason are addressed.</p>
            
            <p>Best regards,<br>MSafiri Team</p>
        </div>
        """
        
        logger.info(f"Sending rejection email to: {participant_email}")
        await send_email(
            to_email=participant_email,
            subject=subject,
            html_content=html_content
        )
        logger.info(f"Rejection email sent successfully to {participant_email}")
            
    except Exception as e:
        logger.error(f"Failed to send per diem rejection email: {e}", exc_info=True)
        print(f"Failed to send per diem rejection email: {e}")

@router.post("/{tenant_slug}/per-diem-approvals/{request_id}/cancel")
async def cancel_tenant_perdiem_approval(
    tenant_slug: str,
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an approved per diem request (Per Diem Approver only)"""
    
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
        Event.tenant_id == tenant.id,
        PerdiemRequest.status == "approved"
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Approved request not found")
    
    if request.approved_by != current_user.email:
        raise HTTPException(status_code=403, detail="Only the original approver can cancel this approval")
    
    # Reset to pending status
    request.status = "pending_approval"
    request.approved_by = None
    request.approved_at = None
    request.approver_role = None
    request.approver_full_name = None
    request.budget_code = None
    request.activity_code = None
    request.cost_center = None
    request.section = None
    
    db.commit()
    return {"message": "Approval cancelled successfully"}


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
    
    # If no daily rate provided, try to get from tenant setup
    if not daily_rate:
        setup = db.query(PerDiemSetup).filter(PerDiemSetup.tenant_id == tenant.id).first()
        if setup:
            daily_rate = float(setup.daily_rate)
            currency = setup.currency
        else:
            raise HTTPException(status_code=400, detail="Daily rate is required or setup per diem configuration")
    
    request.daily_rate = daily_rate
    request.currency = currency
    request.total_amount = daily_rate * request.requested_days
    request.status = "issued"
    
    db.commit()
    return {"message": "Per diem issued successfully"}