from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.db.database import get_db
from app.models.event_agenda import EventAgenda
from pydantic import BaseModel
from datetime import date

router = APIRouter()

class AgendaItemCreate(BaseModel):
    day_number: int
    event_date: str
    time: str
    title: str
    description: str = None

class AgendaDocumentUpdate(BaseModel):
    document_url: str = None

@router.post("/", response_model=dict)
def create_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_in: AgendaItemCreate
) -> Any:
    """Create agenda item"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create agenda item
    agenda_item = EventAgenda(
        event_id=event_id,
        day_number=item_in.day_number,
        event_date=date.fromisoformat(item_in.event_date),
        time=item_in.time,
        title=item_in.title,
        description=item_in.description,
        created_by='admin'
    )
    
    db.add(agenda_item)
    db.commit()
    db.refresh(agenda_item)
    
    return {
        "id": agenda_item.id,
        "day_number": agenda_item.day_number,
        "event_date": agenda_item.event_date.isoformat(),
        "time": agenda_item.time,
        "title": agenda_item.title,
        "description": agenda_item.description,
        "created_by": agenda_item.created_by,
        "created_at": agenda_item.created_at.isoformat()
    }

@router.get("/", response_model=List[dict])
def get_agenda_items(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get agenda items grouped by day"""
    
    items = db.query(EventAgenda).filter(
        EventAgenda.event_id == event_id
    ).order_by(EventAgenda.day_number, EventAgenda.time).all()
    
    return [
        {
            "id": item.id,
            "day_number": item.day_number,
            "event_date": item.event_date.isoformat(),
            "time": item.time,
            "title": item.title,
            "description": item.description,
            "created_by": item.created_by,
            "created_at": item.created_at.isoformat()
        }
        for item in items
    ]

@router.delete("/{item_id}/")
def delete_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_id: int
) -> Any:
    """Delete agenda item"""
    
    item = db.query(EventAgenda).filter(
        EventAgenda.id == item_id,
        EventAgenda.event_id == event_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Agenda item not found")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Agenda item deleted successfully"}

@router.put("/document", response_model=dict)
def update_agenda_document(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    document_in: AgendaDocumentUpdate
) -> Any:
    """Update event agenda document URL"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update event agenda_document_url field
    event.agenda_document_url = document_in.document_url
    db.commit()
    
    return {
        "message": "Agenda document URL updated successfully",
        "document_url": event.agenda_document_url
    }

@router.get("/document", response_model=dict)
def get_agenda_document(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get event agenda document URL"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {
        "document_url": getattr(event, 'agenda_document_url', None)
    }