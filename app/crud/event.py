# File: app/crud/event.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate

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
        
        db_obj = Event(**event_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

event = CRUDEvent(Event)