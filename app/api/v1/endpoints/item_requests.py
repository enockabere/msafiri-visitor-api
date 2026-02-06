from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from app.db.database import get_db
from app.models.item_request import ItemRequest, RequestStatus
from app.models.event_allocation import ParticipantAllocation, EventItem
from app.models.event_participant import EventParticipant
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/{participant_id}/request")
def request_items(
    participant_id: int,
    allocation_ids: List[int],
    notes: str = None,
    db: Session = Depends(get_db)
):
    """Participant requests their allocated items"""
    
    # Verify allocations exist and have remaining items
    for allocation_id in allocation_ids:
        allocation = db.query(ParticipantAllocation).filter(
            and_(
                ParticipantAllocation.id == allocation_id,
                ParticipantAllocation.participant_id == participant_id
            )
        ).first()
        
        if not allocation:
            raise HTTPException(status_code=404, detail=f"Allocation {allocation_id} not found")
        
        remaining = allocation.allocated_quantity - allocation.redeemed_quantity
        if remaining <= 0:
            raise HTTPException(status_code=400, detail=f"No items remaining for allocation {allocation_id}")
        
        # Create request
        request = ItemRequest(
            participant_id=participant_id,
            allocation_id=allocation_id,
            requested_quantity=remaining,
            notes=notes
        )
        db.add(request)
    
    db.commit()
    return {"message": "Item request submitted", "status": "pending"}

@router.get("/pending", response_model=List[dict])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Staff gets pending item requests"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = db.query(
        ItemRequest, ParticipantAllocation, EventItem, EventParticipant
    ).join(
        ParticipantAllocation, ItemRequest.allocation_id == ParticipantAllocation.id
    ).join(
        EventItem, ParticipantAllocation.item_id == EventItem.id
    ).join(
        EventParticipant, ItemRequest.participant_id == EventParticipant.id
    ).filter(ItemRequest.status == RequestStatus.PENDING).all()
    
    result = []
    for request, allocation, item, participant in requests:
        result.append({
            "request_id": request.id,
            "participant_name": participant.full_name,
            "participant_email": participant.email,
            "item_name": item.item_name,
            "item_type": item.item_type.value,
            "requested_quantity": request.requested_quantity,
            "notes": request.notes,
            "created_at": request.created_at
        })
    
    return result

@router.post("/{request_id}/approve")
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Staff approves item request - participant can now collect"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(ItemRequest).filter(ItemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = RequestStatus.APPROVED
    request.approved_by = current_user.email
    db.commit()
    
    return {"message": "Request approved - participant can collect items"}

@router.post("/{request_id}/fulfill")
def fulfill_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Staff fulfills request by giving items to participant"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(ItemRequest).filter(ItemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != RequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Request must be approved first")
    
    # Update allocation
    allocation = db.query(ParticipantAllocation).filter(
        ParticipantAllocation.id == request.allocation_id
    ).first()
    
    allocation.redeemed_quantity += request.requested_quantity
    request.status = RequestStatus.FULFILLED
    
    db.commit()
    return {"message": "Items given to participant", "status": "fulfilled"}
