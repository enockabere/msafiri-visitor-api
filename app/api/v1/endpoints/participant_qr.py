from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
import qrcode
import io
import base64
import json
import uuid
from typing import List
from app.db.database import get_db
from app.models.participant_qr import ParticipantQR
from app.models.event_participant import EventParticipant
from app.models.allocation import EventAllocation
from app.models.inventory import Inventory
from app.models.event import Event
from app.schemas.participant_qr import ParticipantQRResponse, QRAllocationData, AllocationItem
from app.api.deps import get_current_user
from app.models.user import User
from datetime import datetime

router = APIRouter()

@router.get("/{participant_id}/qr", response_model=ParticipantQRResponse)
def generate_participant_qr(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get participant
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    # Get event allocations for this participant's event
    allocations = db.query(EventAllocation).filter(
        EventAllocation.event_id == participant.event_id
    ).all()
    
    # Build allocation data
    allocation_items = []
    total_items = total_drinks = remaining_items = remaining_drinks = 0
    qr_redeemed_drinks = 0
    
    for allocation in allocations:
        # Parse items from allocation notes if available
        items = []
        if allocation.notes and allocation.notes.startswith("ITEMS:"):
            try:
                import json
                items_str = allocation.notes.split("|NOTES:")[0].replace("ITEMS:", "")
                items = json.loads(items_str.replace("'", '"'))
            except:
                pass
        elif allocation.inventory_item_id and allocation.quantity_per_participant > 0:
            items = [{
                "inventory_item_id": allocation.inventory_item_id,
                "quantity_per_event": allocation.quantity_per_participant
            }]
        
        # Add inventory items
        for item_data in items:
            inventory_item = db.query(Inventory).filter(
                Inventory.id == item_data["inventory_item_id"]
            ).first()
            
            if inventory_item:
                quantity = item_data.get("quantity_per_event", item_data.get("quantity_per_participant", 0))
                allocation_items.append(AllocationItem(
                    item_name=inventory_item.name,
                    item_type="PHYSICAL",  # Default type
                    allocated_quantity=quantity,
                    redeemed_quantity=0,  # No redemption tracking yet
                    remaining_quantity=quantity
                ))
                total_items += quantity
                remaining_items += quantity
        
        # Add drink vouchers (check participant-specific redemptions)
        if hasattr(allocation, 'drink_vouchers_per_participant') and allocation.drink_vouchers_per_participant > 0:
            # Get participant-specific redemptions from database
            from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
            
            redemptions = db.query(ParticipantVoucherRedemption).filter(
                ParticipantVoucherRedemption.allocation_id == allocation.id,
                ParticipantVoucherRedemption.participant_id == participant_id
            ).all()
            
            net_redeemed = sum(r.quantity for r in redemptions)
            original_quantity = allocation.drink_vouchers_per_participant
            remaining_quantity = original_quantity - net_redeemed
            
            total_drinks = original_quantity
            remaining_drinks = remaining_quantity
            qr_redeemed_drinks = max(0, net_redeemed)  # Don't show negative redeemed
            break  # Only need one allocation for voucher count
    
    qr_data = QRAllocationData(
        participant_id=participant.id,
        participant_name=participant.full_name or "Unknown",
        participant_email=participant.email,
        event_id=event.id if event else 0,
        event_title=event.title if event else "Unknown Event",
        event_location=event.location if event else "Unknown Location",
        event_start_date=event.start_date.isoformat() if event and event.start_date else None,
        event_end_date=event.end_date.isoformat() if event and event.end_date else None,
        total_drinks=total_drinks,
        remaining_drinks=remaining_drinks,
        redeemed_drinks=locals().get('qr_redeemed_drinks', 0)
    )
    
    # Check if QR already exists
    existing_qr = db.query(ParticipantQR).filter(ParticipantQR.participant_id == participant_id).first()
    
    if existing_qr:
        qr_token = existing_qr.qr_token
        # Update QR data
        existing_qr.qr_data = qr_data.json()
        db.commit()
    else:
        # Create new QR
        qr_token = str(uuid.uuid4())
        new_qr = ParticipantQR(
            participant_id=participant_id,
            qr_token=qr_token,
            qr_data=qr_data.json()
        )
        db.add(new_qr)
        db.commit()
    
    # Generate QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return ParticipantQRResponse(
        qr_token=qr_token,
        qr_data_url=f"data:image/png;base64,{img_str}",
        allocation_summary=qr_data
    )

@router.get("/scan/{qr_token}", response_model=QRAllocationData)
def scan_qr_code(qr_token: str, db: Session = Depends(get_db)):
    qr_record = db.query(ParticipantQR).filter(ParticipantQR.qr_token == qr_token).first()
    if not qr_record:
        raise HTTPException(status_code=404, detail="Invalid QR code")
    
    return QRAllocationData.parse_raw(qr_record.qr_data)

@router.post("/request-items/{participant_id}")
def request_items_via_qr(
    participant_id: int,
    db: Session = Depends(get_db)
):
    # Get participant
    participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event allocations for this participant's event
    allocations = db.query(EventAllocation).filter(
        EventAllocation.event_id == participant.event_id
    ).all()
    
    if not allocations:
        raise HTTPException(status_code=400, detail="No items available for request")
    
    return {
        "message": "Item requests submitted",
        "status": "pending",
        "instructions": "Wait for staff approval, then present QR code for collection"
    }

@router.post("/{participant_id}/voucher-redeemed-notification")
async def send_voucher_redeemed_notification(
    participant_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Send email notification to participant about voucher redemption"""
    
    try:
        from app.core.email_service import email_service
        
        participant_email = request_data.get("participant_email")
        participant_name = request_data.get("participant_name")
        redeemed_quantity = request_data.get("redeemed_quantity")
        remaining_quantity = request_data.get("remaining_quantity")
        
        if not participant_email:
            raise HTTPException(status_code=400, detail="Participant email is required")
        
        # Get participant and event details
        participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        
        subject = f"Drink Voucher Redemption - {event.title if event else 'Event'}"
        
        message = f"""
        <h2>Drink Voucher Redemption Confirmation</h2>
        
        <p>Dear {participant_name or 'Participant'},</p>
        
        <p>This is to confirm that your drink vouchers have been redeemed successfully.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #d4edda; border-left: 4px solid #28a745;">
            <h3>Redemption Details:</h3>
            <p><strong>Event:</strong> {event.title if event else 'Unknown Event'}</p>
            <p><strong>Redeemed Vouchers:</strong> {redeemed_quantity}</p>
            <p><strong>Remaining Vouchers:</strong> {remaining_quantity}</p>
            <p><strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        </div>
        
        <p>Your QR code has been updated to reflect the new voucher balance.</p>
        
        <p>Thank you for participating in our event!</p>
        """
        
        # Send email notification
        email_service.send_notification_email(
            to_email=participant_email,
            user_name=participant_name or participant_email,
            title=subject,
            message=message
        )
        
        return {
            "message": "Voucher redemption notification sent successfully",
            "email": participant_email,
            "redeemed_quantity": redeemed_quantity,
            "remaining_quantity": remaining_quantity
        }
        
    except Exception as e:
        print(f"Error sending voucher redemption notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")