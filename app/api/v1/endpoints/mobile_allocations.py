from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.event_participant import EventParticipant
from app.models.allocation import EventAllocation
from app.models.event import Event
from app.core.deps import get_current_user
from pydantic import BaseModel
from typing import List, Optional
import qrcode
import io
import base64
from datetime import datetime
import secrets

router = APIRouter()

class VoucherRedemptionRequest(BaseModel):
    quantity: int
    notes: Optional[str] = None

class QRCodeResponse(BaseModel):
    qr_token: str
    qr_data_url: str
    participant_id: int
    event_id: int
    total_vouchers: int
    remaining_vouchers: int
    redemption_quantity: int

@router.get("/participant/allocations")
def get_participant_allocations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get allocations for current participant"""
    
    try:
        print(f"🔍 ALLOCATIONS DEBUG: Starting allocation fetch for user: {current_user.email}")
        
        # Get participant records for current user
        participants = db.query(EventParticipant).filter(
            EventParticipant.email == current_user.email
        ).all()
        
        print(f"🔍 ALLOCATIONS DEBUG: Found {len(participants)} participants for user {current_user.email}")
        
        if not participants:
            print(f"🔍 ALLOCATIONS DEBUG: No participants found, returning empty allocations")
            return {"allocations": []}
        
        all_allocations = []
        
        for participant in participants:
            print(f"🔍 ALLOCATIONS DEBUG: Processing participant {participant.id} for event {participant.event_id}")
            
            # Get event details
            event = db.query(Event).filter(Event.id == participant.event_id).first()
            if not event:
                print(f"🔍 ALLOCATIONS DEBUG: No event found for event_id {participant.event_id}")
                continue
                
            print(f"🔍 ALLOCATIONS DEBUG: Found event: {event.title}")
                
            # Get voucher allocations for this event
            voucher_allocations = db.query(EventAllocation).filter(
                EventAllocation.event_id == participant.event_id,
                EventAllocation.drink_vouchers_per_participant > 0
            ).all()
            
            print(f"🔍 ALLOCATIONS DEBUG: Found {len(voucher_allocations)} voucher allocations for event {participant.event_id}")
            
            for allocation in voucher_allocations:
                print(f"🔍 ALLOCATIONS DEBUG: Processing allocation {allocation.id} with {allocation.drink_vouchers_per_participant} vouchers")
                
                # Calculate remaining vouchers for this participant
                try:
                    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
                    
                    redemptions = db.query(ParticipantVoucherRedemption).filter(
                        ParticipantVoucherRedemption.allocation_id == allocation.id,
                        ParticipantVoucherRedemption.participant_id == participant.id
                    ).all()
                    
                    total_redeemed = sum(r.quantity for r in redemptions)
                except Exception as redemption_error:
                    print(f"🔍 ALLOCATIONS DEBUG: Error querying redemptions (table may not exist): {redemption_error}")
                    total_redeemed = 0
                
                remaining = allocation.drink_vouchers_per_participant - total_redeemed
                
                print(f"🔍 ALLOCATIONS DEBUG: Allocation {allocation.id} - Total: {allocation.drink_vouchers_per_participant}, Redeemed: {total_redeemed}, Remaining: {remaining}")
                
                allocation_data = {
                    "id": allocation.id,
                    "participant_id": participant.id,
                    "event_id": event.id,
                    "event_title": event.title,
                    "event_location": event.location,
                    "allocation_type": "drink_vouchers",
                    "total_quantity": allocation.drink_vouchers_per_participant,
                    "remaining_quantity": remaining,
                    "redeemed_quantity": max(0, total_redeemed),
                    "status": allocation.status,
                    "created_at": allocation.created_at.isoformat() if allocation.created_at else None
                }
                
                all_allocations.append(allocation_data)
                print(f"🔍 ALLOCATIONS DEBUG: Added allocation to list: {allocation_data}")
        
        print(f"🔍 ALLOCATIONS DEBUG: Returning {len(all_allocations)} total allocations")
        return {"allocations": all_allocations}
        
    except Exception as e:
        print(f"❌ ALLOCATIONS ERROR: {str(e)}")
        import traceback
        print(f"❌ ALLOCATIONS TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching allocations: {str(e)}")

@router.post("/participant/voucher-redemption/initiate")
def initiate_voucher_redemption(
    request: VoucherRedemptionRequest,
    allocation_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate voucher redemption process - generates QR code for scanning"""
    
    # Get participant
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get allocation
    allocation = db.query(EventAllocation).filter(
        EventAllocation.id == allocation_id
    ).first()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    # Check remaining vouchers
    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
    
    redemptions = db.query(ParticipantVoucherRedemption).filter(
        ParticipantVoucherRedemption.allocation_id == allocation_id,
        ParticipantVoucherRedemption.participant_id == participant.id
    ).all()
    
    total_redeemed = sum(r.quantity for r in redemptions)
    remaining = allocation.drink_vouchers_per_participant - total_redeemed
    
    if request.quantity > remaining:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot redeem {request.quantity} vouchers. Only {remaining} remaining."
        )
    
    # Generate redemption token
    redemption_token = secrets.token_urlsafe(32)
    
    # Store pending redemption
    from app.models.pending_voucher_redemption import PendingVoucherRedemption
    
    pending_redemption = PendingVoucherRedemption(
        token=redemption_token,
        allocation_id=allocation_id,
        participant_id=participant.id,
        quantity=request.quantity,
        notes=request.notes,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(pending_redemption)
    db.commit()
    
    # Generate QR code
    qr_data = {
        "type": "voucher_redemption",
        "token": redemption_token,
        "participant_id": participant.id,
        "allocation_id": allocation_id,
        "quantity": request.quantity,
        "participant_name": participant.full_name,
        "event_id": allocation.event_id
    }
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"msafiri://redeem/{redemption_token}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    qr_data_url = f"data:image/png;base64,{base64.b64encode(img_buffer.getvalue()).decode()}"
    
    return QRCodeResponse(
        qr_token=redemption_token,
        qr_data_url=qr_data_url,
        participant_id=participant.id,
        event_id=allocation.event_id,
        total_vouchers=allocation.drink_vouchers_per_participant,
        remaining_vouchers=remaining,
        redemption_quantity=request.quantity
    )

@router.get("/admin/scan-redemption/{token}")
def get_redemption_details(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get redemption details for admin scanning (admin users only)"""
    
    # Check if user is admin for any event
    if not current_user.role or current_user.role not in ["ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get pending redemption
    from app.models.pending_voucher_redemption import PendingVoucherRedemption
    
    pending = db.query(PendingVoucherRedemption).filter(
        PendingVoucherRedemption.token == token,
        PendingVoucherRedemption.status == "pending"
    ).first()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Redemption request not found or already processed")
    
    # Get participant and allocation details
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == pending.participant_id
    ).first()
    
    allocation = db.query(EventAllocation).filter(
        EventAllocation.id == pending.allocation_id
    ).first()
    
    event = db.query(Event).filter(Event.id == allocation.event_id).first()
    
    return {
        "token": token,
        "participant_id": pending.participant_id,
        "participant_name": participant.full_name if participant else "Unknown",
        "participant_email": participant.email if participant else "Unknown",
        "event_title": event.title if event else "Unknown Event",
        "quantity": pending.quantity,
        "notes": pending.notes,
        "created_at": pending.created_at.isoformat(),
        "allocation_id": pending.allocation_id,
        "total_vouchers": allocation.drink_vouchers_per_participant if allocation else 0
    }

@router.post("/admin/confirm-redemption/{token}")
def confirm_voucher_redemption(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm voucher redemption (admin users only)"""
    
    # Check if user is admin
    if not current_user.role or current_user.role not in ["ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get pending redemption
    from app.models.pending_voucher_redemption import PendingVoucherRedemption
    
    pending = db.query(PendingVoucherRedemption).filter(
        PendingVoucherRedemption.token == token,
        PendingVoucherRedemption.status == "pending"
    ).first()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Redemption request not found or already processed")
    
    # Create actual redemption record
    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
    
    redemption = ParticipantVoucherRedemption(
        allocation_id=pending.allocation_id,
        participant_id=pending.participant_id,
        quantity=pending.quantity,
        redeemed_at=datetime.utcnow(),
        redeemed_by=current_user.email,
        notes=pending.notes
    )
    
    db.add(redemption)
    
    # Mark pending as completed
    pending.status = "completed"
    pending.processed_at = datetime.utcnow()
    pending.processed_by = current_user.email
    
    db.commit()
    
    # Calculate new remaining balance
    allocation = db.query(EventAllocation).filter(
        EventAllocation.id == pending.allocation_id
    ).first()
    
    all_redemptions = db.query(ParticipantVoucherRedemption).filter(
        ParticipantVoucherRedemption.allocation_id == pending.allocation_id,
        ParticipantVoucherRedemption.participant_id == pending.participant_id
    ).all()
    
    total_redeemed = sum(r.quantity for r in all_redemptions)
    remaining = allocation.drink_vouchers_per_participant - total_redeemed
    
    return {
        "message": "Voucher redemption confirmed successfully",
        "redeemed_quantity": pending.quantity,
        "total_redeemed": total_redeemed,
        "remaining_vouchers": remaining
    }

@router.post("/participant/voucher-redemption/complete")
def complete_voucher_redemption(
    request: dict,
    db: Session = Depends(get_db)
):
    """Complete voucher redemption from QR scanner"""
    
    try:
        print(f"🔍 REDEMPTION DEBUG: Received request: {request}")
        
        # Handle comprehensive voucher data format
        if 'allocation_id' in request and 'quantity' in request:
            allocation_id = int(request['allocation_id'])
            quantity = int(request['quantity'])
            scanner_email = request.get('scanner_email')
            
            print(f"🔍 REDEMPTION DEBUG: Processing allocation {allocation_id}, quantity {quantity}")
            
            # Get allocation
            allocation = db.query(EventAllocation).filter(
                EventAllocation.id == allocation_id
            ).first()
            
            if not allocation:
                raise HTTPException(status_code=404, detail="Allocation not found")
            
            # Get participant from allocation's event
            participant = db.query(EventParticipant).filter(
                EventParticipant.event_id == allocation.event_id
            ).first()
            
            if not participant:
                raise HTTPException(status_code=404, detail="Participant not found")
            
            # Create redemption record
            from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
            
            redemption = ParticipantVoucherRedemption(
                allocation_id=allocation_id,
                participant_id=participant.id,
                quantity=quantity,
                redeemed_at=datetime.utcnow(),
                redeemed_by=scanner_email or "scanner",
                notes=f"Scanned redemption via mobile app"
            )
            
            db.add(redemption)
            db.commit()
            
            print(f"🔍 REDEMPTION DEBUG: Successfully created redemption record")
            
            return {
                "success": True,
                "message": "Voucher redeemed successfully",
                "participant_name": participant.full_name,
                "quantity": quantity
            }
        
        # Handle token-based redemption (fallback)
        elif 'qr_token' in request:
            token = request['qr_token']
            scanner_email = request.get('scanner_email')
            
            print(f"🔍 REDEMPTION DEBUG: Processing token {token}")
            
            from app.models.pending_voucher_redemption import PendingVoucherRedemption
            
            pending = db.query(PendingVoucherRedemption).filter(
                PendingVoucherRedemption.token == token,
                PendingVoucherRedemption.status == "pending"
            ).first()
            
            if not pending:
                raise HTTPException(status_code=404, detail="Redemption token not found or already processed")
            
            # Create actual redemption record
            from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
            
            redemption = ParticipantVoucherRedemption(
                allocation_id=pending.allocation_id,
                participant_id=pending.participant_id,
                quantity=pending.quantity,
                redeemed_at=datetime.utcnow(),
                redeemed_by=scanner_email or "scanner",
                notes=pending.notes
            )
            
            db.add(redemption)
            
            # Mark pending as completed
            pending.status = "completed"
            pending.processed_at = datetime.utcnow()
            pending.processed_by = scanner_email or "scanner"
            
            db.commit()
            
            participant = db.query(EventParticipant).filter(
                EventParticipant.id == pending.participant_id
            ).first()
            
            return {
                "success": True,
                "message": "Voucher redeemed successfully",
                "participant_name": participant.full_name if participant else "Unknown",
                "quantity": pending.quantity
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid request format")
            
    except Exception as e:
        print(f"❌ REDEMPTION ERROR: {str(e)}")
        import traceback
        print(f"❌ REDEMPTION TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing redemption: {str(e)}")

@router.get("/admin/pending-redemptions")
def get_pending_redemptions(
    event_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending redemptions for admin review"""
    
    # Check if user is admin
    if not current_user.role or current_user.role not in ["ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.models.pending_voucher_redemption import PendingVoucherRedemption
    
    query = db.query(PendingVoucherRedemption).filter(
        PendingVoucherRedemption.status == "pending"
    )
    
    if event_id:
        # Filter by event through allocation
        query = query.join(EventAllocation).filter(EventAllocation.event_id == event_id)
    
    pending_redemptions = query.all()
    
    result = []
    for pending in pending_redemptions:
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == pending.participant_id
        ).first()
        
        allocation = db.query(EventAllocation).filter(
            EventAllocation.id == pending.allocation_id
        ).first()
        
        event = db.query(Event).filter(Event.id == allocation.event_id).first() if allocation else None
        
        result.append({
            "token": pending.token,
            "participant_name": participant.full_name if participant else "Unknown",
            "event_title": event.title if event else "Unknown Event",
            "quantity": pending.quantity,
            "created_at": pending.created_at.isoformat(),
            "notes": pending.notes
        })
    
    return {"pending_redemptions": result}