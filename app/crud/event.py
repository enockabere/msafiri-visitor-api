# File: app/crud/event.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate
from sqlalchemy.orm import joinedload

class CRUDEvent(CRUDBase[Event, EventCreate, EventUpdate]):
    
    def get_by_tenant(self, db: Session, *, tenant_id: int, skip: int = 0, limit: int = 100) -> List[Event]:
        return (
            db.query(Event)
            .filter(Event.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_tenant(self, db: Session, *, obj_in: EventCreate, tenant_id: int, created_by: str) -> Event:
        event_data = obj_in.dict()
        event_data["tenant_id"] = tenant_id
        event_data["created_by"] = created_by
        
        # If vendor_accommodation_id is provided, populate location data from the hotel
        if event_data.get("vendor_accommodation_id"):
            from app.models.guesthouse import VendorAccommodation
            vendor = db.query(VendorAccommodation).filter(
                VendorAccommodation.id == event_data["vendor_accommodation_id"]
            ).first()
            if vendor:
                event_data["location"] = vendor.location
                event_data["address"] = vendor.location  # Use location as address
                if vendor.latitude:
                    event_data["latitude"] = float(vendor.latitude)
                if vendor.longitude:
                    event_data["longitude"] = float(vendor.longitude)
        
        db_obj = Event(**event_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, *, db_obj: Event, obj_in: EventUpdate) -> Event:
        update_data = obj_in.dict(exclude_unset=True)
        
        # If vendor_accommodation_id is being updated, populate location data from the hotel
        if "vendor_accommodation_id" in update_data and update_data["vendor_accommodation_id"]:
            from app.models.guesthouse import VendorAccommodation
            vendor = db.query(VendorAccommodation).filter(
                VendorAccommodation.id == update_data["vendor_accommodation_id"]
            ).first()
            if vendor:
                update_data["location"] = vendor.location
                update_data["address"] = vendor.location  # Use location as address
                if vendor.latitude:
                    update_data["latitude"] = float(vendor.latitude)
                if vendor.longitude:
                    update_data["longitude"] = float(vendor.longitude)
        
        return super().update(db, db_obj=db_obj, obj_in=update_data)
    
    def get_published_events(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Event]:
        """Get all published events regardless of tenant for mobile app"""
        return (
            db.query(Event)
            .filter(Event.status.ilike('published'))
            .order_by(Event.start_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_ids(self, db: Session, *, event_ids: List[int]) -> List[Event]:
        """Get events by list of IDs"""
        return (
            db.query(Event)
            .filter(Event.id.in_(event_ids))
            .all()
        )

event = CRUDEvent(Event)
