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
    db: Session = Depends(get_db)
):
    print(f"\n=== QR GENERATION START FOR PARTICIPANT {participant_id} ===")
    print(f"DEBUG QR: Function called at {datetime.now()}")
    try:
        # Get participant
        print(f"DEBUG QR: Looking for participant with ID {participant_id}")
        participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
        if not participant:
            print(f"DEBUG QR: Participant {participant_id} not found in database")
            # Check if participant exists at all
            all_participants = db.query(EventParticipant).all()
            print(f"DEBUG QR: Total participants in database: {len(all_participants)}")
            for p in all_participants[:5]:  # Show first 5
                print(f"DEBUG QR: - Participant ID {p.id}, Event {p.event_id}, Email {p.email}")
            raise HTTPException(status_code=404, detail="Participant not found")
        
        print(f"DEBUG QR: Found participant {participant.id} for event {participant.event_id}")
        
        # Get event
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        print(f"DEBUG QR: Event found: {event.title if event else 'None'}")
        
        # Get event allocations for this participant's event
        print(f"DEBUG QR: About to query EventAllocation for event_id {participant.event_id}")
        try:
            allocations = db.query(EventAllocation).filter(
                EventAllocation.event_id == participant.event_id
            ).all()
            print(f"DEBUG QR: Successfully queried {len(allocations)} allocations for event {participant.event_id}")
        except Exception as e:
            print(f"DEBUG QR: Error querying allocations: {e}")
            import traceback
            print(f"DEBUG QR: Query error traceback: {traceback.format_exc()}")
            allocations = []
        
        print(f"DEBUG QR: Participant ID {participant_id}, Event ID {participant.event_id}, Status {participant.status}")
        print(f"DEBUG QR: Found {len(allocations)} allocations for event {participant.event_id}")
        
        if len(allocations) == 0:
            # Check if there are any allocations at all
            all_allocations = db.query(EventAllocation).all()
            print(f"DEBUG QR: Total allocations in database: {len(all_allocations)}")
            for a in all_allocations[:3]:  # Show first 3
                print(f"DEBUG QR: - Allocation ID {a.id}, Event {a.event_id}, Vouchers {getattr(a, 'drink_vouchers_per_participant', 0)}")
        
        # Build allocation data
        allocation_items = []
        total_items = total_drinks = remaining_items = remaining_drinks = 0
        qr_redeemed_drinks = 0
        
        for allocation in allocations:
            print(f"DEBUG QR: Processing allocation ID {allocation.id}")
            print(f"DEBUG QR: - All allocation attributes: {dir(allocation)}")
            print(f"DEBUG QR: - drink_vouchers_per_participant: {getattr(allocation, 'drink_vouchers_per_participant', 'NOT_FOUND')}")
            print(f"DEBUG QR: - quantity_per_participant: {getattr(allocation, 'quantity_per_participant', 'NOT_FOUND')}")
            print(f"DEBUG QR: - status: {getattr(allocation, 'status', 'NOT_FOUND')}")
            print(f"DEBUG QR: - notes: {getattr(allocation, 'notes', 'NOT_FOUND')}")
            print(f"DEBUG QR: - tenant_id: {getattr(allocation, 'tenant_id', 'NOT_FOUND')}")
            print(f"DEBUG QR: - event_id: {getattr(allocation, 'event_id', 'NOT_FOUND')}")
            print(f"DEBUG QR: - allocation_type: {getattr(allocation, 'allocation_type', 'NOT_FOUND')}")
            
            # Parse items from allocation notes if available
            items = []
            if allocation.notes and allocation.notes.startswith("ITEMS:"):
                try:
                    import json
                    items_str = allocation.notes.split("|NOTES:")[0].replace("ITEMS:", "")
                    items = json.loads(items_str.replace("'", '"'))
                    print(f"DEBUG QR: - parsed items: {items}")
                except Exception as e:
                    print(f"DEBUG QR: - error parsing items: {e}")
                    pass
            elif allocation.inventory_item_id and allocation.quantity_per_participant > 0:
                items = [{
                    "inventory_item_id": allocation.inventory_item_id,
                    "quantity_per_event": allocation.quantity_per_participant
                }]
                print(f"DEBUG QR: - fallback items: {items}")
            
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
            
            # Add drink vouchers (check for drink_vouchers_per_participant field)
            vouchers_per_participant = 0
            if hasattr(allocation, 'drink_vouchers_per_participant') and allocation.drink_vouchers_per_participant > 0:
                vouchers_per_participant = allocation.drink_vouchers_per_participant
                print(f"DEBUG QR: Found drink_vouchers_per_participant: {vouchers_per_participant}")
            elif hasattr(allocation, 'vouchers_per_participant') and allocation.vouchers_per_participant > 0:
                vouchers_per_participant = allocation.vouchers_per_participant
                print(f"DEBUG QR: Found vouchers_per_participant: {vouchers_per_participant}")
            elif getattr(allocation, 'allocation_type', None) == 'drink_vouchers':
                vouchers_per_participant = getattr(allocation, 'quantity_per_participant', 0)
                print(f"DEBUG QR: Found allocation_type drink_vouchers: {vouchers_per_participant}")
            else:
                print(f"DEBUG QR: No vouchers found for allocation {allocation.id}")
                print(f"DEBUG QR: - Allocation has drink_vouchers_per_participant = {getattr(allocation, 'drink_vouchers_per_participant', None)}")
                print(f"DEBUG QR: - hasattr check: {hasattr(allocation, 'drink_vouchers_per_participant')}")
                
            if vouchers_per_participant > 0:
                print(f"DEBUG: Found {vouchers_per_participant} vouchers for participant {participant_id}")
                # Get participant-specific redemptions from database
                try:
                    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
                    redemptions = db.query(ParticipantVoucherRedemption).filter(
                        ParticipantVoucherRedemption.allocation_id == allocation.id,
                        ParticipantVoucherRedemption.participant_id == participant_id
                    ).all()
                    net_redeemed = sum(r.quantity for r in redemptions)
                except:
                    net_redeemed = 0
                
                total_drinks = vouchers_per_participant
                remaining_drinks = vouchers_per_participant - net_redeemed
                qr_redeemed_drinks = max(0, net_redeemed)
                print(f"DEBUG QR: Set total_drinks={total_drinks}, remaining_drinks={remaining_drinks}, redeemed={qr_redeemed_drinks}")
                break
        
        print(f"DEBUG QR: Final voucher totals - total_drinks={total_drinks}, remaining_drinks={remaining_drinks}")
        print(f"DEBUG QR: QR data will show: total_drinks={total_drinks}, remaining_drinks={remaining_drinks}, redeemed_drinks={qr_redeemed_drinks}")
        
        # Create QR data with safe defaults
        try:
            qr_data = QRAllocationData(
                participant_id=participant.id,
                participant_name=participant.full_name or "Unknown",
                participant_email=participant.email or "unknown@example.com",
                event_id=event.id if event else 0,
                event_title=event.title if event else "Unknown Event",
                event_location=event.location if event else "Unknown Location",
                event_start_date=event.start_date.isoformat() if event and event.start_date else None,
                event_end_date=event.end_date.isoformat() if event and event.end_date else None,
                total_drinks=total_drinks,
                remaining_drinks=remaining_drinks,
                redeemed_drinks=qr_redeemed_drinks
            )
            print(f"DEBUG QR: QR data created successfully")
        except Exception as e:
            print(f"DEBUG QR: Error creating QR data: {e}")
            raise e
        
        # Check if QR already exists - handle transaction errors
        print(f"DEBUG QR: Checking for existing QR for participant {participant_id}")
        existing_qr = None
        try:
            db.rollback()  # Clear any failed transaction first
            existing_qr = db.query(ParticipantQR).filter(ParticipantQR.participant_id == participant_id).first()
            print(f"DEBUG QR: Existing QR found: {existing_qr is not None}")
        except Exception as e:
            print(f"DEBUG QR: Error checking existing QR: {e}")
            db.rollback()
            existing_qr = None
        
        # Use existing token or create new one
        if existing_qr:
            qr_token = existing_qr.qr_token
            print(f"DEBUG QR: Using existing QR token {qr_token}")
            # Update existing record with latest data
            try:
                existing_qr.qr_data = qr_data.json()
                db.commit()
                print(f"DEBUG QR: Updated existing QR record")
            except Exception as e:
                print(f"DEBUG QR: Error updating QR record: {e}")
                db.rollback()
        else:
            qr_token = str(uuid.uuid4())
            print(f"DEBUG QR: Creating new QR token {qr_token}")
            
            # Store QR data in database with upsert logic
            try:
                # Try to insert new record
                new_qr = ParticipantQR(
                    participant_id=participant_id,
                    qr_token=qr_token,
                    qr_data=qr_data.json()
                )
                db.add(new_qr)
                db.commit()
                print(f"DEBUG QR: Stored new QR record in database")
            except Exception as e:
                print(f"DEBUG QR: Error storing QR record: {e}")
                db.rollback()
                # If insert failed due to duplicate, try to update existing record
                try:
                    existing_qr = db.query(ParticipantQR).filter(ParticipantQR.participant_id == participant_id).first()
                    if existing_qr:
                        qr_token = existing_qr.qr_token  # Use existing token
                        existing_qr.qr_data = qr_data.json()  # Update data
                        db.commit()
                        print(f"DEBUG QR: Updated existing QR record with token {qr_token}")
                    else:
                        print(f"DEBUG QR: Continuing with temporary token {qr_token}")
                except Exception as e2:
                    print(f"DEBUG QR: Error updating existing QR record: {e2}")
                    db.rollback()
                    print(f"DEBUG QR: Continuing with temporary token {qr_token}")
                    # Continue with temporary token - it won't be scannable but QR will still generate
        
        # Generate QR code image with full URL
        print(f"DEBUG QR: Generating QR code image for token {qr_token}")
        try:
            from PIL import Image
            # Create full URL for QR code using environment variable
            import os
            print(f"\n--- ENVIRONMENT VARIABLE DEBUGGING ---")
            frontend_url_raw = os.getenv('FRONTEND_URL')
            print(f"DEBUG QR: Raw FRONTEND_URL from os.getenv(): '{frontend_url_raw}'")
            print(f"DEBUG QR: Type of FRONTEND_URL: {type(frontend_url_raw)}")
            
            base_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            print(f"DEBUG QR: Resolved base_url with fallback: '{base_url}'")
            
            # Check all environment variables
            frontend_vars = [(k, v) for k, v in os.environ.items() if 'FRONTEND' in k.upper()]
            print(f"DEBUG QR: All FRONTEND environment variables: {frontend_vars}")
            
            # Check common URL environment variables
            url_vars = [(k, v) for k, v in os.environ.items() if any(term in k.upper() for term in ['URL', 'HOST', 'DOMAIN'])]
            print(f"DEBUG QR: All URL-related environment variables: {url_vars[:10]}...")  # Limit output
            
            qr_url = f"{base_url}/public/qr/{qr_token}"
            print(f"DEBUG QR: Final constructed QR code URL: '{qr_url}'")
            print(f"--- END ENVIRONMENT DEBUGGING ---\n")
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            print(f"DEBUG QR: QR code image generated successfully, length: {len(img_str)}")
        except Exception as e:
            print(f"DEBUG QR: Error generating QR image: {e}")
            import traceback
            print(f"DEBUG QR: QR generation traceback: {traceback.format_exc()}")
            # Return a simple base64 placeholder image
            img_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        print(f"DEBUG QR: Returning QR response with total_drinks={qr_data.total_drinks}")
        print(f"DEBUG QR: Response will contain token: {qr_token}")
        print(f"DEBUG QR: Response image data length: {len(img_str)}")
        print(f"=== QR GENERATION END FOR PARTICIPANT {participant_id} ===\n")
        
        return ParticipantQRResponse(
            qr_token=qr_token,
            qr_data_url=f"data:image/png;base64,{img_str}",
            allocation_summary=qr_data
        )
    except Exception as e:
        print(f"\n!!! ERROR in QR generation for participant {participant_id}: {e}")
        import traceback
        print(f"!!! ERROR traceback: {traceback.format_exc()}")
        print(f"=== QR GENERATION FAILED FOR PARTICIPANT {participant_id} ===\n")
        try:
            db.rollback()  # Rollback any failed transaction
        except:
            pass
        raise HTTPException(status_code=500, detail=f"QR generation failed: {str(e)}")

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