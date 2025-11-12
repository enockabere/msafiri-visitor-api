# File: app/api/v1/endpoints/allocations.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.allocation import EventAllocation
from app.models.inventory import Inventory
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.user import User
from app.schemas.allocation import AllocationCreate, AllocationUpdate, Allocation
from app.core.email_service import email_service
from app.api.deps import get_current_user
from datetime import datetime

router = APIRouter()

@router.post("/items")
async def create_item_allocation(
    request_data: dict,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create item allocation"""
    
    try:
        event_id = request_data.get("event_id")
        items = request_data.get("items", [])
        notes = request_data.get("notes", "")
        category = request_data.get("category", "")
        requested_email = request_data.get("requested_email", "")
        
        if not items:
            raise HTTPException(status_code=400, detail="Items are required")
        
        # Create allocation with items
        items_json = [{"inventory_item_id": item["inventory_item_id"], "quantity_per_event": item["quantity_per_event"]} for item in items]
        first_item = items[0]
        
        db_allocation = EventAllocation(
            event_id=event_id,
            inventory_item_id=first_item["inventory_item_id"],
            quantity_per_participant=first_item["quantity_per_event"],
            drink_vouchers_per_participant=0,
            notes=f"ITEMS:{items_json}|NOTES:{notes}|EMAIL:{requested_email}|CATEGORY:{category}",
            status="open",
            tenant_id=tenant_id,
            created_by=created_by
        )
        
        db.add(db_allocation)
        db.commit()
        db.refresh(db_allocation)
        
        # Get inventory item details for email
        items_with_names = []
        for item in items_json:
            inventory_item = db.query(Inventory).filter(Inventory.id == item["inventory_item_id"]).first()
            items_with_names.append({
                "inventory_item_name": inventory_item.name if inventory_item else f"Item {item['inventory_item_id']}",
                "quantity_per_event": item["quantity_per_event"]
            })
        
        # Send email notification
        await send_item_request_email(db_allocation, db, tenant_id, requested_email, category, items_with_names)
        
        return {"message": "Item allocation created successfully", "id": db_allocation.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create item allocation: {str(e)}")

@router.post("/vouchers")
async def create_voucher_allocation(
    request_data: dict,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create voucher allocation"""
    
    try:
        print(f"DEBUG VOUCHER: Request data: {request_data}")
        print(f"DEBUG VOUCHER: tenant_id={tenant_id}, created_by={created_by}")
        
        event_id = request_data.get("event_id")
        drink_vouchers_per_participant = request_data.get("drink_vouchers_per_participant", 0)
        notes = request_data.get("notes", "")
        
        print(f"DEBUG VOUCHER: event_id={event_id}, vouchers={drink_vouchers_per_participant}")
        
        if drink_vouchers_per_participant <= 0:
            raise HTTPException(status_code=400, detail="Vouchers per participant must be greater than 0")
        
        # Find any inventory item to use as dummy (or create without inventory_item_id constraint)
        dummy_inventory = db.query(Inventory).filter(Inventory.tenant_id == str(tenant_id)).first()
        if not dummy_inventory:
            # If no inventory items exist, create a dummy one
            dummy_inventory = Inventory(
                name="Voucher Placeholder",
                category="voucher",
                quantity=999,
                condition="new",
                tenant_id=tenant_id
            )
            db.add(dummy_inventory)
            db.commit()
            db.refresh(dummy_inventory)
        
        print(f"DEBUG VOUCHER: Using dummy inventory item ID: {dummy_inventory.id}")
        
        # Create voucher-only allocation
        db_allocation = EventAllocation(
            event_id=event_id,
            inventory_item_id=dummy_inventory.id,
            quantity_per_participant=0,
            drink_vouchers_per_participant=drink_vouchers_per_participant,
            notes=f"VOUCHERS_ONLY|NOTES:{notes}",
            status="open",
            tenant_id=tenant_id,
            created_by=created_by
        )
        
        print(f"DEBUG VOUCHER: Creating allocation with data: {db_allocation.__dict__}")
        
        db.add(db_allocation)
        db.commit()
        db.refresh(db_allocation)
        
        print(f"DEBUG VOUCHER: Successfully created allocation ID: {db_allocation.id}")
        
        return {"message": "Voucher allocation created successfully", "id": db_allocation.id}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG VOUCHER ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create voucher allocation: {str(e)}")

@router.post("/", response_model=Allocation)
async def create_allocation(
    allocation: AllocationCreate,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create new event allocation"""
    
    # Validate inventory items if provided
    if allocation.items:
        for item in allocation.items:
            inventory_item = db.query(Inventory).filter(Inventory.id == item.inventory_item_id).first()
            if not inventory_item:
                raise HTTPException(status_code=404, detail=f"Inventory item {item.inventory_item_id} not found")
    
    # Create single allocation with items as JSON
    try:
        # Check if we have either items or vouchers
        if not allocation.items and allocation.drink_vouchers_per_participant == 0:
            raise HTTPException(status_code=400, detail="Must allocate either items or vouchers")
        
        # Handle items if provided
        if allocation.items:
            # Store items as JSON in notes field
            items_json = [{"inventory_item_id": item.inventory_item_id, "quantity_per_event": item.quantity_per_event} for item in allocation.items]
            
            # Use first item for main fields
            first_item = allocation.items[0]
            
            db_allocation = EventAllocation(
                event_id=allocation.event_id,
                inventory_item_id=first_item.inventory_item_id,
                quantity_per_participant=first_item.quantity_per_event,
                drink_vouchers_per_participant=allocation.drink_vouchers_per_participant,
                notes=f"ITEMS:{items_json}|NOTES:{allocation.notes or ''}",
                status=allocation.status or "open",
                tenant_id=tenant_id,
                created_by=created_by
            )
        else:
            # Voucher-only allocation
            db_allocation = EventAllocation(
                event_id=allocation.event_id,
                inventory_item_id=1,  # Use dummy item ID for voucher-only allocations
                quantity_per_participant=0,
                drink_vouchers_per_participant=allocation.drink_vouchers_per_participant,
                notes=f"VOUCHERS_ONLY|NOTES:{allocation.notes or ''}",
                status=allocation.status or "open",
                tenant_id=tenant_id,
                created_by=created_by
            )
        
        db.add(db_allocation)
        db.commit()
        db.refresh(db_allocation)
        
        # Send notification to HR Admin only if pending
        if db_allocation.status == "pending":
            await notify_hr_admin(db_allocation, db, tenant_id)
        
        return get_allocation_with_details(db_allocation, db)
        
    except Exception as e:
        db.rollback()
        print(f"Error creating allocation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create allocation: {str(e)}")

@router.get("/event/{event_id}", response_model=List[Allocation])
async def get_event_allocations(
    event_id: int,
    tenant_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Get all allocations for an event"""
    
    print(f"DEBUG EVENT ALLOCATIONS: Looking for event_id={event_id}, tenant_id={tenant_id}")
    
    # Build query based on whether tenant_id is provided
    query = db.query(EventAllocation).filter(EventAllocation.event_id == event_id)
    if tenant_id is not None:
        query = query.filter(EventAllocation.tenant_id == tenant_id)
    
    allocations = query.all()
    
    print(f"DEBUG EVENT ALLOCATIONS: Found {len(allocations)} allocations")
    for alloc in allocations:
        print(f"DEBUG EVENT ALLOCATIONS: ID={alloc.id}, Status={alloc.status}, Event={alloc.event_id}, Tenant={alloc.tenant_id}")
    
    return [get_allocation_with_details(allocation, db) for allocation in allocations]

@router.get("/items/event/{event_id}")
async def get_event_item_allocations(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get item allocations for an event"""
    
    allocations = db.query(EventAllocation).filter(
        EventAllocation.event_id == event_id,
        EventAllocation.tenant_id == tenant_id
    ).all()
    
    # Filter for allocations with items (not voucher-only)
    item_allocations = []
    for allocation in allocations:
        allocation_details = get_allocation_with_details(allocation, db)
        if allocation_details.get("items"):
            # Extract email and category from notes
            notes = allocation.notes or ""
            requested_email = "admin@msf.org"
            category = "equipment"
            
            if "|EMAIL:" in notes:
                email_part = notes.split("|EMAIL:")[1].split("|CATEGORY:")[0] if "|CATEGORY:" in notes else notes.split("|EMAIL:")[1].split("|NOTES:")[0] if "|NOTES:" in notes else notes.split("|EMAIL:")[1]
                requested_email = email_part.strip()
            
            if "|CATEGORY:" in notes:
                category_part = notes.split("|CATEGORY:")[1].split("|NOTES:")[0] if "|NOTES:" in notes else notes.split("|CATEGORY:")[1]
                category = category_part.strip()
            
            # Convert to item allocation format
            for item in allocation_details["items"]:
                # Get actual category from inventory item
                inventory_item = db.query(Inventory).filter(Inventory.id == item["inventory_item_id"]).first()
                actual_category = inventory_item.category if inventory_item else category
                
                item_allocations.append({
                    "id": allocation.id,
                    "inventory_item_id": item["inventory_item_id"],
                    "inventory_item_name": item["inventory_item_name"],
                    "inventory_item_category": actual_category,
                    "quantity_per_event": item["quantity_per_event"],
                    "available_quantity": item["available_quantity"],
                    "status": allocation.status,
                    "notes": allocation_details["notes"],
                    "created_by": allocation.created_by,
                    "approved_by": allocation.approved_by,
                    "created_at": allocation.created_at.isoformat() if allocation.created_at else None,
                    "requested_email": requested_email
                })
    
    return item_allocations

@router.get("/vouchers/event/{event_id}")
async def get_event_voucher_allocations(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get voucher allocations for an event"""
    
    allocations = db.query(EventAllocation).filter(
        EventAllocation.event_id == event_id,
        EventAllocation.tenant_id == tenant_id,
        EventAllocation.drink_vouchers_per_participant > 0
    ).all()
    
    # Convert to voucher allocation format
    voucher_allocations = []
    for allocation in allocations:
        voucher_allocations.append({
            "id": allocation.id,
            "drink_vouchers_per_participant": allocation.drink_vouchers_per_participant,
            "status": allocation.status,
            "notes": allocation.notes,
            "created_by": allocation.created_by,
            "approved_by": allocation.approved_by,
            "created_at": allocation.created_at.isoformat() if allocation.created_at else None
        })
    
    return voucher_allocations

@router.get("/participant/{participant_id}")
async def get_participant_allocations(
    participant_id: int,
    event_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Get allocations for a specific participant"""
    
    # Get participant to verify they exist
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get event allocations for this participant's event
    query = db.query(EventAllocation).filter(
        EventAllocation.event_id == participant.event_id
    )
    
    if event_id:
        query = query.filter(EventAllocation.event_id == event_id)
    
    allocations = query.all()
    
    # Convert to participant-specific allocations
    participant_allocations = []
    for allocation in allocations:
        # Always show drink voucher allocations if they exist
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
            
            participant_allocations.append({
                "id": allocation.id,
                "allocation_type": "drink_voucher",
                "quantity": original_quantity,  # Original assigned quantity
                "current_quantity": remaining_quantity,  # Current remaining for this participant
                "status": allocation.status,
                "allocated_date": allocation.created_at.isoformat() if allocation.created_at else None,
                "notes": allocation.notes,
                "redeemed": max(0, net_redeemed)  # Don't show negative redeemed
            })
        
        # Add inventory items as separate allocations
        allocation_details = get_allocation_with_details(allocation, db)
        for item in allocation_details.get("items", []):
            if item.get("quantity_per_event", item.get("quantity_per_participant", 0)) > 0:
                participant_allocations.append({
                    "id": f"{allocation.id}_{item['inventory_item_id']}",
                    "allocation_type": item["inventory_item_name"].lower().replace(" ", "_"),
                    "quantity": item.get("quantity_per_event", item.get("quantity_per_participant", 0)),
                    "status": allocation.status,
                    "allocated_date": allocation.created_at.isoformat() if allocation.created_at else None,
                    "notes": f"ITEMS:{allocation.notes}" if allocation.notes else "ITEMS:Event allocation"
                })
    
    return participant_allocations

@router.get("/pending", response_model=List[dict])
async def get_pending_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending allocations for HR approval"""
    
    # Get tenant ID from user's tenant_id or return empty if none
    if not current_user.tenant_id:
        return []
    
    # Handle both string and int tenant_id
    tenant_id = current_user.tenant_id if isinstance(current_user.tenant_id, int) else int(current_user.tenant_id)
    
    allocations = db.query(EventAllocation).filter(
        EventAllocation.tenant_id == tenant_id,
        EventAllocation.status == "pending"
    ).all()
    
    result = []
    for allocation in allocations:
        allocation_data = get_allocation_with_details(allocation, db)
        # Add event details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        allocation_data["event_title"] = event.title if event else "Unknown Event"
        allocation_data["event_date"] = event.start_date.isoformat() if event and event.start_date else None
        result.append(allocation_data)
    
    return result

@router.get("/debug-all")
async def debug_all_allocations(db: Session = Depends(get_db)):
    """Debug endpoint to show all allocations"""
    print("=== DEBUG ALL ALLOCATIONS ===")
    
    all_allocations = db.query(EventAllocation).all()
    print(f"Total allocations in database: {len(all_allocations)}")
    
    for alloc in all_allocations:
        print(f"ID: {alloc.id}, Status: {alloc.status}, Event: {alloc.event_id}, Tenant: {alloc.tenant_id}, Created: {alloc.created_at}")
    
    print("=== END DEBUG ===")
    
    return {
        "total_allocations": len(all_allocations),
        "allocations": [
            {
                "id": alloc.id,
                "status": alloc.status,
                "event_id": alloc.event_id,
                "tenant_id": alloc.tenant_id
            } for alloc in all_allocations
        ]
    }

@router.get("/fix-tenant-id")
async def fix_tenant_id(db: Session = Depends(get_db)):
    """Fix tenant_id from 1 to 2 for existing allocations"""
    print("=== FIXING TENANT IDs ===")
    
    allocations = db.query(EventAllocation).filter(EventAllocation.tenant_id == 1).all()
    print(f"Found {len(allocations)} allocations with tenant_id=1")
    
    for alloc in allocations:
        print(f"Updating allocation ID {alloc.id} from tenant_id=1 to tenant_id=2")
        alloc.tenant_id = 2
    
    db.commit()
    print("=== TENANT IDs FIXED ===")
    
    return {"message": f"Updated {len(allocations)} allocations to tenant_id=2"}

@router.post("/request-items")
async def request_items(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Send item request email for a specific category"""
    try:
        event_id = request_data.get("event_id")
        category = request_data.get("category")
        email = request_data.get("email")
        tenant_id = request_data.get("tenant_id")
        
        # Get event details
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get allocations for this category
        allocations = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id,
            EventAllocation.tenant_id == tenant_id
        ).all()
        
        # Filter items by category
        category_items = []
        for allocation in allocations:
            allocation_details = get_allocation_with_details(allocation, db)
            for item in allocation_details.get("items", []):
                # Get inventory item to check category
                inventory_item = db.query(Inventory).filter(
                    Inventory.id == item["inventory_item_id"]
                ).first()
                
                if inventory_item and inventory_item.category == category:
                    category_items.append({
                        "name": item["inventory_item_name"],
                        "quantity": item["quantity_per_event"],
                        "category": inventory_item.category
                    })
        
        if not category_items:
            return {"message": "No items found for this category"}
        
        # Format category name
        category_display = {
            "ict_equipment": "ICT Equipment/Items",
            "equipment": "Equipment",
            "stationary": "Stationary"
        }.get(category, category.title())
        
        # Create email content
        items_list = "\n".join([f"• {item['name']} - Quantity: {item['quantity']}" for item in category_items])
        
        subject = f"Item Request - {event.title} ({category_display})"
        message = f"""
        <h2>Item Request for Event: {event.title}</h2>
        
        <h3>Event Details:</h3>
        <p><strong>Event:</strong> {event.title}</p>
        <p><strong>Location:</strong> {event.location or 'TBD'}</p>
        <p><strong>Start Date:</strong> {event.start_date}</p>
        <p><strong>End Date:</strong> {event.end_date}</p>
        
        <h3>Requested Items ({category_display}):</h3>
        <ul>
        {''.join([f'<li>{item["name"]} - Quantity: {item["quantity"]}</li>' for item in category_items])}
        </ul>
        
        <p>Please prepare these items for the event.</p>
        """
        
        # Send email (mock implementation)
        print(f"Sending email to {email}:")
        print(f"Subject: {subject}")
        print(f"Content: {message}")
        
        return {
            "message": "Item request sent successfully",
            "email": email,
            "category": category_display,
            "items_count": len(category_items)
        }
        
    except Exception as e:
        print(f"Error sending item request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send item request: {str(e)}")

@router.get("/test/{tenant_slug}")
async def test_endpoint(tenant_slug: str):
    """Test endpoint"""
    print(f"TEST: Endpoint called with tenant_slug: {tenant_slug}")
    return {"message": f"Test successful for {tenant_slug}"}

@router.get("/voucher-stats/{event_id}")
async def get_voucher_stats(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get voucher statistics for an event"""
    
    # Get event participants
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).all()
    
    # Get voucher allocations for this event
    voucher_allocations = db.query(EventAllocation).filter(
        EventAllocation.event_id == event_id,
        EventAllocation.tenant_id == tenant_id,
        EventAllocation.drink_vouchers_per_participant > 0
    ).all()
    
    total_participants = len(participants)
    vouchers_per_participant = sum(alloc.drink_vouchers_per_participant for alloc in voucher_allocations)
    total_allocated_vouchers = vouchers_per_participant * total_participants
    
    # Calculate actual redeemed vouchers from redemption records
    total_redeemed_vouchers = 0
    if voucher_allocations:
        try:
            from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
            from sqlalchemy import func
            
            # Sum all redemptions for all allocations in this event
            for allocation in voucher_allocations:
                redeemed_sum = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
                    ParticipantVoucherRedemption.allocation_id == allocation.id
                ).scalar() or 0
                total_redeemed_vouchers += redeemed_sum
                
        except Exception as e:
            print(f"Error calculating redeemed vouchers: {e}")
            total_redeemed_vouchers = 0
    
    return {
        "total_participants": total_participants,
        "total_allocated_vouchers": total_allocated_vouchers,
        "total_redeemed_vouchers": total_redeemed_vouchers
    }

@router.get("/pending/{tenant_slug}", response_model=List[dict])
async def get_pending_allocations_by_tenant(
    tenant_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending allocations for HR approval by tenant slug"""
    
    print(f"DEBUG: Looking for tenant with slug: {tenant_slug}")
    
    # Convert tenant slug to tenant ID by looking up the tenant
    from app.models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        print(f"DEBUG: Tenant not found for slug: {tenant_slug}")
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    print(f"DEBUG: Found tenant ID: {tenant.id}")
    
    # Check all allocations for this tenant
    all_allocations = db.query(EventAllocation).filter(EventAllocation.tenant_id == tenant.id).all()
    print(f"DEBUG: Total allocations for tenant {tenant.id}: {len(all_allocations)}")
    for alloc in all_allocations:
        print(f"DEBUG: Allocation ID {alloc.id}, Status: {alloc.status}, Tenant ID: {alloc.tenant_id}")
    
    allocations = db.query(EventAllocation).filter(
        EventAllocation.tenant_id == tenant.id,
        EventAllocation.status == "pending"
    ).all()
    
    print(f"DEBUG: Pending allocations found: {len(allocations)}")
    
    result = []
    for allocation in allocations:
        print(f"DEBUG: Processing allocation ID: {allocation.id}")
        allocation_data = get_allocation_with_details(allocation, db)
        # Add event details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        allocation_data["event_title"] = event.title if event else "Unknown Event"
        allocation_data["event_date"] = event.start_date.isoformat() if event and event.start_date else None
        result.append(allocation_data)
    
    print(f"DEBUG: Returning {len(result)} allocations")
    return result
    
    result = []
    for allocation in allocations:
        allocation_data = get_allocation_with_details(allocation, db)
        # Add event details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        allocation_data["event_title"] = event.title if event else "Unknown Event"
        allocation_data["event_date"] = event.start_date.isoformat() if event and event.start_date else None
        result.append(allocation_data)
    
    return result

@router.put("/{allocation_id}/approve")
async def approve_allocation(
    allocation_id: int,
    approved_by: str = Query(...),
    comment: str = Query(None),
    db: Session = Depends(get_db)
):
    """Approve allocation (HR Admin only)"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    allocation.status = "approved"
    allocation.approved_by = approved_by
    allocation.approved_at = datetime.utcnow()
    
    # Add approval comment if provided
    if comment:
        existing_notes = allocation.notes or ""
        if "|NOTES:" in existing_notes:
            user_notes = existing_notes.split("|NOTES:")[1]
            items_part = existing_notes.split("|NOTES:")[0]
            allocation.notes = f"{items_part}|NOTES:{user_notes}|APPROVED: {comment}"
        else:
            allocation.notes = f"{existing_notes}|APPROVED: {comment}"
    
    db.commit()
    
    return {"message": "Allocation approved successfully"}

@router.put("/{allocation_id}/reject")
async def reject_allocation(
    allocation_id: int,
    approved_by: str = Query(...),
    comment: str = Query(...),
    db: Session = Depends(get_db)
):
    """Reject allocation (HR Admin only)"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    if not comment:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    allocation.status = "rejected"
    allocation.approved_by = approved_by
    allocation.approved_at = datetime.utcnow()
    
    # Add rejection comment
    existing_notes = allocation.notes or ""
    if "|NOTES:" in existing_notes:
        user_notes = existing_notes.split("|NOTES:")[1]
        items_part = existing_notes.split("|NOTES:")[0]
        allocation.notes = f"{items_part}|NOTES:{user_notes}|REJECTED: {comment}"
    else:
        allocation.notes = f"{existing_notes}|REJECTED: {comment}"
    
    db.commit()
    
    return {"message": "Allocation rejected successfully"}

@router.put("/{allocation_id}/cancel")
async def cancel_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    """Cancel pending allocation to allow editing"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    if allocation.status != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending allocations")
    
    allocation.status = "open"
    allocation.approved_by = None
    allocation.approved_at = None
    
    db.commit()
    
    return {"message": "Allocation cancelled and available for editing"}

@router.put("/{allocation_id}")
async def update_allocation(
    allocation_id: int,
    allocation_update: AllocationUpdate,
    db: Session = Depends(get_db)
):
    """Update allocation (only if status is draft)"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    if allocation.status not in ["open", "draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only edit open, draft or rejected allocations")
    
    # Update simple fields
    if allocation_update.drink_vouchers_per_participant is not None:
        allocation.drink_vouchers_per_participant = allocation_update.drink_vouchers_per_participant
    if allocation_update.notes is not None:
        allocation.notes = allocation_update.notes
    if allocation_update.status is not None:
        allocation.status = allocation_update.status
    
    # Handle items update
    if allocation_update.items and len(allocation_update.items) > 0:
        items_json = [{"inventory_item_id": item.inventory_item_id, "quantity_per_event": item.quantity_per_event} for item in allocation_update.items]
        first_item = allocation_update.items[0]
        allocation.inventory_item_id = first_item.inventory_item_id
        allocation.quantity_per_participant = first_item.quantity_per_event
        
        # Update notes with new items
        existing_notes = allocation.notes or ""
        if "|NOTES:" in existing_notes:
            user_notes = existing_notes.split("|NOTES:")[1]
        else:
            user_notes = existing_notes
        allocation.notes = f"ITEMS:{items_json}|NOTES:{user_notes}"
    
    db.commit()
    
    return get_allocation_with_details(allocation, db)

@router.delete("/items/{allocation_id}")
async def delete_item_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    """Delete item allocation"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Item allocation not found")
    
    db.delete(allocation)
    db.commit()
    
    return {"message": "Item allocation deleted successfully"}

@router.delete("/vouchers/{allocation_id}")
async def delete_voucher_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    """Delete voucher allocation"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Voucher allocation not found")
    
    db.delete(allocation)
    db.commit()
    
    return {"message": "Voucher allocation deleted successfully"}

@router.delete("/{allocation_id}")
async def delete_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    """Delete allocation"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    db.delete(allocation)
    db.commit()
    
    return {"message": "Allocation deleted successfully"}

@router.put("/{allocation_id}/resubmit")
async def resubmit_allocation(
    allocation_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Resubmit allocation for approval"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    if allocation.status not in ["open", "draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only resubmit open, draft or rejected allocations")
    
    allocation.status = "pending"
    allocation.approved_by = None
    allocation.approved_at = None
    # Clear previous notes
    
    db.commit()
    
    # Send notification to HR Admin
    await notify_hr_admin(allocation, db, tenant_id)
    
    return {"message": "Allocation resubmitted for approval"}

def get_allocation_with_details(allocation: EventAllocation, db: Session) -> dict:
    """Get allocation with inventory item details"""
    # Parse items from notes if stored as JSON
    items = []
    user_notes = ""
    
    if allocation.notes and allocation.notes.startswith("ITEMS:"):
        try:
            import json
            parts = allocation.notes.split("|NOTES:")
            items_str = parts[0].replace("ITEMS:", "")
            items = json.loads(items_str.replace("'", '"'))
            user_notes = parts[1] if len(parts) > 1 else ""
        except:
            user_notes = allocation.notes
    elif allocation.notes and allocation.notes.startswith("VOUCHERS_ONLY"):
        # Voucher-only allocation
        items = []
        parts = allocation.notes.split("|NOTES:")
        user_notes = parts[1] if len(parts) > 1 else ""
    else:
        user_notes = allocation.notes or ""
        # Fallback to single item only if not voucher-only
        if allocation.inventory_item_id and allocation.quantity_per_participant > 0:
            items = [{
                "inventory_item_id": allocation.inventory_item_id,
                "quantity_per_event": allocation.quantity_per_participant
            }]
    
    # Get inventory details for items
    items_with_details = []
    for item in items:
        try:
            inventory_item = db.query(Inventory).filter(Inventory.id == item["inventory_item_id"]).first()
            items_with_details.append({
                "inventory_item_id": item["inventory_item_id"],
                "quantity_per_event": item.get("quantity_per_event", item.get("quantity_per_participant", 0)),
                "inventory_item_name": inventory_item.name if inventory_item else f"Item {item['inventory_item_id']}",
                "available_quantity": inventory_item.quantity if inventory_item else 0
            })
        except Exception as e:
            print(f"Error fetching inventory item {item['inventory_item_id']}: {e}")
            items_with_details.append({
                "inventory_item_id": item["inventory_item_id"],
                "quantity_per_event": item.get("quantity_per_event", item.get("quantity_per_participant", 0)),
                "inventory_item_name": f"Item {item['inventory_item_id']}",
                "available_quantity": 0
            })
    
    return {
        "id": allocation.id,
        "event_id": allocation.event_id,
        "items": items_with_details,
        "drink_vouchers_per_participant": allocation.drink_vouchers_per_participant,
        "status": allocation.status,
        "notes": user_notes,
        "tenant_id": allocation.tenant_id,
        "created_by": allocation.created_by,
        "approved_by": allocation.approved_by,
        "created_at": allocation.created_at,
        "approved_at": allocation.approved_at
    }

@router.post("/{allocation_id}/redeem")
async def redeem_voucher(
    allocation_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Redeem drink vouchers from an allocation for a specific participant"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    quantity = request_data.get("quantity", 1)
    participant_id = request_data.get("participant_id")
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if not participant_id:
        raise HTTPException(status_code=400, detail="Participant ID is required")
    
    # Create redemption record
    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
    
    redemption = ParticipantVoucherRedemption(
        allocation_id=allocation_id,
        participant_id=participant_id,
        quantity=quantity,
        redeemed_at=datetime.utcnow()
    )
    
    db.add(redemption)
    db.commit()
    
    # Calculate totals for this participant
    redemptions = db.query(ParticipantVoucherRedemption).filter(
        ParticipantVoucherRedemption.allocation_id == allocation_id,
        ParticipantVoucherRedemption.participant_id == participant_id
    ).all()
    
    net_redeemed = sum(r.quantity for r in redemptions)
    
    remaining = allocation.drink_vouchers_per_participant - net_redeemed
    
    return {
        "message": "Vouchers redeemed successfully",
        "redeemed_quantity": quantity,
        "total_redeemed": net_redeemed,
        "remaining_quantity": remaining,
        "over_redeemed": max(0, -remaining)
    }

@router.post("/{allocation_id}/reassign")
async def reassign_voucher(
    allocation_id: int,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Re-assign drink vouchers to a participant (reverse redemption)"""
    
    allocation = db.query(EventAllocation).filter(EventAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    quantity = request_data.get("quantity", 1)
    participant_id = request_data.get("participant_id")
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if not participant_id:
        raise HTTPException(status_code=400, detail="Participant ID is required")
    
    # Create negative redemption record (reassignment)
    from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
    
    reassignment = ParticipantVoucherRedemption(
        allocation_id=allocation_id,
        participant_id=participant_id,
        quantity=-quantity,  # Negative for reassignment
        redeemed_at=datetime.utcnow()
    )
    
    db.add(reassignment)
    db.commit()
    
    # Calculate totals for this participant
    redemptions = db.query(ParticipantVoucherRedemption).filter(
        ParticipantVoucherRedemption.allocation_id == allocation_id,
        ParticipantVoucherRedemption.participant_id == participant_id
    ).all()
    
    net_redeemed = sum(r.quantity for r in redemptions)
    
    remaining = allocation.drink_vouchers_per_participant - net_redeemed
    
    return {
        "message": "Vouchers reassigned successfully",
        "reassigned_quantity": quantity,
        "total_redeemed": net_redeemed,
        "remaining_quantity": remaining
    }

async def send_item_request_email(allocation: EventAllocation, db: Session, tenant_id: int, email: str, category: str, items: list):
    """Send item request email to specified recipient"""
    try:
        # Get event details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        if not event:
            print("Event not found for email notification")
            return
        
        # Format items list
        items_list = "\n".join([f"• {item.get('inventory_item_name', 'Item')} - Quantity: {item['quantity_per_event']}" for item in items])
        
        # Format category name
        category_display = {
            "ict_equipment": "ICT Equipment/Items",
            "equipment": "Equipment", 
            "stationary": "Stationery"
        }.get(category, category.title())
        
        subject = f"Item Request - {event.title} ({category_display})"
        message = f"""
        <h2>Item Request for Event: {event.title}</h2>
        
        <h3>Event Details:</h3>
        <p><strong>Event:</strong> {event.title}</p>
        <p><strong>Location:</strong> {event.location or 'TBD'}</p>
        <p><strong>Start Date:</strong> {event.start_date}</p>
        <p><strong>End Date:</strong> {event.end_date}</p>
        
        <h3>Requested Items ({category_display}):</h3>
        <div style="margin: 10px 0;">
        {items_list.replace(chr(10), '<br>')}
        </div>
        
        <p>Please prepare these items for the event.</p>
        <p>If you have any questions, please contact the event organizer.</p>
        """
        
        # Send email using the email service
        email_service.send_notification_email(
            to_email=email,
            user_name=email.split('@')[0],
            title=subject,
            message=message
        )
        
        print(f"Item request email sent to {email} for event {event.title}")
        
    except Exception as e:
        print(f"Error sending item request email: {e}")

async def notify_hr_admin(allocation: EventAllocation, db: Session, tenant_id: int):
    """Send notification to HR Admin for allocation approval"""
    try:
        # Find HR Admin for this tenant
        hr_admin = db.query(User).filter(
            User.tenant_id == str(tenant_id),
            User.role == "HR_ADMIN"
        ).first()
        
        if not hr_admin:
            print("No HR Admin found for tenant")
            return
        
        # Get event details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        
        # Get event and inventory details
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        inventory_item = db.query(Inventory).filter(Inventory.id == allocation.inventory_item_id).first()
        
        subject = f"Allocation Approval Required - {event.title if event else 'Event'}"
        
        message = f"""
        <p>Dear {hr_admin.full_name or hr_admin.email},</p>
        <p>A new resource allocation request requires your approval.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
            <h3>Allocation Details:</h3>
            <p><strong>Event:</strong> {event.title if event else 'Unknown'}</p>
            <p><strong>Item:</strong> {inventory_item.name if inventory_item else 'Unknown'}</p>
            <p><strong>Quantity per participant:</strong> {allocation.quantity_per_participant}</p>
            <p><strong>Drink vouchers per participant:</strong> {allocation.drink_vouchers_per_participant}</p>
            <p><strong>Requested by:</strong> {allocation.created_by}</p>
        </div>
        
        <p>Please review and approve/reject this allocation request through the admin portal.</p>
        """
        
        # Send email notification
        email_service.send_notification_email(
            to_email=hr_admin.email,
            user_name=hr_admin.full_name or hr_admin.email,
            title=subject,
            message=message
        )
        
        print(f"Allocation approval notification sent to HR Admin: {hr_admin.email}")
        
    except Exception as e:
        print(f"Error sending HR Admin notification: {e}")