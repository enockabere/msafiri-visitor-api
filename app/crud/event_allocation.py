# File: app/crud/event_allocation.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.event_allocation import EventItem, ParticipantAllocation, RedemptionLog
from app.schemas.event_allocation import EventItemCreate, ParticipantAllocationCreate

class CRUDEventItem(CRUDBase[EventItem, EventItemCreate, dict]):
    
    def get_by_event(self, db: Session, *, event_id: int) -> List[EventItem]:
        return db.query(EventItem).filter(EventItem.event_id == event_id).all()
    
    def create_item(self, db: Session, *, event_id: int, item_data: EventItemCreate, created_by: str) -> EventItem:
        item = EventItem(
            event_id=event_id,
            item_name=item_data.item_name,
            item_type=item_data.item_type,
            description=item_data.description,
            total_quantity=item_data.total_quantity,
            created_by=created_by
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

class CRUDParticipantAllocation(CRUDBase[ParticipantAllocation, ParticipantAllocationCreate, dict]):
    
    def get_by_participant(self, db: Session, *, participant_id: int) -> List[ParticipantAllocation]:
        return db.query(ParticipantAllocation).filter(
            ParticipantAllocation.participant_id == participant_id
        ).all()
    
    def get_by_event(self, db: Session, *, event_id: int) -> List[ParticipantAllocation]:
        return db.query(ParticipantAllocation).join(EventItem).filter(
            EventItem.event_id == event_id
        ).all()
    
    def create_allocation(self, db: Session, *, participant_id: int, item_id: int, quantity: int, allocated_by: str) -> ParticipantAllocation:
        allocation = ParticipantAllocation(
            participant_id=participant_id,
            item_id=item_id,
            allocated_quantity=quantity,
            allocated_by=allocated_by
        )
        db.add(allocation)
        
        # Update item allocated quantity
        item = db.query(EventItem).filter(EventItem.id == item_id).first()
        if item:
            item.allocated_quantity += quantity
        
        db.commit()
        db.refresh(allocation)
        return allocation
    
    def redeem_item(self, db: Session, *, allocation_id: int, quantity: int, redeemed_by: str, notes: str = None) -> ParticipantAllocation:
        allocation = db.query(ParticipantAllocation).filter(
            ParticipantAllocation.id == allocation_id
        ).first()
        
        if allocation and allocation.redeemed_quantity + quantity <= allocation.allocated_quantity + allocation.extra_requested:
            allocation.redeemed_quantity += quantity
            
            # Log the redemption
            log = RedemptionLog(
                allocation_id=allocation_id,
                quantity_redeemed=quantity,
                redeemed_by=redeemed_by,
                notes=notes
            )
            db.add(log)
            
            db.commit()
            db.refresh(allocation)
        
        return allocation
    
    def request_extra(self, db: Session, *, allocation_id: int, extra_quantity: int) -> ParticipantAllocation:
        allocation = db.query(ParticipantAllocation).filter(
            ParticipantAllocation.id == allocation_id
        ).first()
        
        if allocation:
            allocation.extra_requested += extra_quantity
            db.commit()
            db.refresh(allocation)
        
        return allocation

class CRUDRedemptionLog(CRUDBase[RedemptionLog, dict, dict]):
    
    def get_by_allocation(self, db: Session, *, allocation_id: int) -> List[RedemptionLog]:
        return db.query(RedemptionLog).filter(
            RedemptionLog.allocation_id == allocation_id
        ).all()

event_item = CRUDEventItem(EventItem)
participant_allocation = CRUDParticipantAllocation(ParticipantAllocation)
redemption_log = CRUDRedemptionLog(RedemptionLog)