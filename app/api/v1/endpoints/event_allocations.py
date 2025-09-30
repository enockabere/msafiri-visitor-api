# File: app/api/v1/endpoints/event_allocations.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

def can_manage_events(user_role: UserRole) -> bool:
    """Check if user role can manage events"""
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    return user_role in admin_roles

@router.post("/{event_id}/items", response_model=schemas.EventItem)
def create_event_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_data: schemas.EventItemCreate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create item for event allocation."""
    
    # Check permissions
    if not can_manage_events(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can create event items"
        )
    
    # Check if event exists and user can access it
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create items for events from other tenants"
        )
    
    item = crud.event_item.create_item(
        db, event_id=event_id, item_data=item_data, created_by=current_user.email
    )
    return item

@router.get("/{event_id}/items", response_model=List[schemas.EventItem])
def get_event_items(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get all items for an event."""
    
    # Check if event exists and user can access it
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user.role != UserRole.SUPER_ADMIN and event.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access items from other tenants"
        )
    
    items = crud.event_item.get_by_event(db, event_id=event_id)
    return items

@router.post("/{event_id}/allocations", response_model=List[schemas.ParticipantAllocation])
def allocate_items_to_participants(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    allocation_request: schemas.AllocateItemsRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Allocate items to participants."""
    
    # Check permissions
    if not can_manage_events(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can allocate items"
        )
    
    # Check if event exists and user can access it
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot allocate items for events from other tenants"
        )
    
    # Check if item exists
    item = crud.event_item.get(db, id=allocation_request.item_id)
    if not item or item.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found for this event"
        )
    
    # Check if enough quantity available
    total_needed = len(allocation_request.participant_ids) * allocation_request.quantity_per_participant
    available = item.total_quantity - item.allocated_quantity
    
    if total_needed > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough items available. Need {total_needed}, have {available}"
        )
    
    allocations = []
    for participant_id in allocation_request.participant_ids:
        # Check if participant exists for this event
        participant = crud.event_participant.get(db, id=participant_id)
        if not participant or participant.event_id != event_id:
            continue
        
        allocation = crud.participant_allocation.create_allocation(
            db,
            participant_id=participant_id,
            item_id=allocation_request.item_id,
            quantity=allocation_request.quantity_per_participant,
            allocated_by=current_user.email
        )
        allocations.append(allocation)
    
    return allocations

@router.get("/{event_id}/allocations", response_model=List[schemas.ParticipantAllocation])
def get_event_allocations(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get all allocations for an event."""
    
    # Check if event exists and user can access it
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user.role != UserRole.SUPER_ADMIN and event.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access allocations from other tenants"
        )
    
    allocations = crud.participant_allocation.get_by_event(db, event_id=event_id)
    return allocations

@router.post("/allocations/redeem", response_model=schemas.ParticipantAllocation)
def redeem_item(
    *,
    db: Session = Depends(get_db),
    redeem_request: schemas.RedeemItemRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Redeem allocated item (staff use)."""
    
    # Check permissions - staff or admin can redeem
    if current_user.role not in [UserRole.STAFF, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff or admin roles can redeem items"
        )
    
    # Get allocation
    allocation = crud.participant_allocation.get(db, id=redeem_request.allocation_id)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )
    
    # Check if enough quantity available to redeem
    available = allocation.allocated_quantity + allocation.extra_requested - allocation.redeemed_quantity
    if redeem_request.quantity > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot redeem {redeem_request.quantity} items. Only {available} available"
        )
    
    updated_allocation = crud.participant_allocation.redeem_item(
        db,
        allocation_id=redeem_request.allocation_id,
        quantity=redeem_request.quantity,
        redeemed_by=current_user.email,
        notes=redeem_request.notes
    )
    
    return updated_allocation

@router.post("/allocations/request-extra", response_model=schemas.ParticipantAllocation)
def request_extra_items(
    *,
    db: Session = Depends(get_db),
    extra_request: schemas.RequestExtraItemRequest,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Request extra items beyond allocation."""
    
    # Get allocation
    allocation = crud.participant_allocation.get(db, id=extra_request.allocation_id)
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allocation not found"
        )
    
    # Check if current user is the participant or an admin
    participant = crud.event_participant.get(db, id=allocation.participant_id)
    if (current_user.email != participant.email and 
        not can_manage_events(current_user.role)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only request extra items for yourself or be an admin"
        )
    
    updated_allocation = crud.participant_allocation.request_extra(
        db,
        allocation_id=extra_request.allocation_id,
        extra_quantity=extra_request.extra_quantity
    )
    
    return updated_allocation

@router.get("/participants/{participant_id}/allocations", response_model=List[schemas.ParticipantAllocation])
def get_participant_allocations(
    *,
    db: Session = Depends(get_db),
    participant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get all allocations for a participant."""
    
    # Get participant
    participant = crud.event_participant.get(db, id=participant_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    # Check if current user is the participant or an admin
    if (current_user.email != participant.email and 
        not can_manage_events(current_user.role)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own allocations or be an admin"
        )
    
    allocations = crud.participant_allocation.get_by_participant(
        db, participant_id=participant_id
    )
    return allocations