from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app import crud
from app.db.database import get_db
from app.models.event_agenda import EventAgenda
from pydantic import BaseModel
from datetime import date

router = APIRouter()

class AgendaItemCreate(BaseModel):
    title: str
    description: str = None
    start_datetime: str
    end_datetime: str
    day_number: int = None
    speaker: str = None
    session_number: str = None

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
    
    from datetime import datetime
    
    # Parse datetime strings
    start_dt = datetime.fromisoformat(item_in.start_datetime.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(item_in.end_datetime.replace('Z', '+00:00'))
    
    # Create agenda item using the new table structure
    event_date = start_dt.date()
    db.execute(
        text("INSERT INTO event_agenda (event_id, title, description, start_datetime, end_datetime, speaker, session_number, day_number, event_date) VALUES (:event_id, :title, :description, :start_dt, :end_dt, :speaker, :session_number, :day_number, :event_date)"),
        {"event_id": event_id, "title": item_in.title, "description": item_in.description, "start_dt": start_dt, "end_dt": end_dt, "speaker": item_in.speaker, "session_number": item_in.session_number, "day_number": item_in.day_number, "event_date": event_date}
    )
    db.commit()
    
    return {
        "message": "Agenda item created successfully",
        "title": item_in.title,
        "start_datetime": item_in.start_datetime,
        "end_datetime": item_in.end_datetime
    }

@router.get("/", response_model=List[dict])
def get_agenda_items(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get agenda items"""
    
    # Use raw SQL to get from the new table structure
    result = db.execute(
        text("SELECT id, title, description, start_datetime, end_datetime, speaker, session_number, created_at FROM event_agenda WHERE event_id = :event_id ORDER BY start_datetime"),
        {"event_id": event_id}
    ).fetchall()
    
    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "start_datetime": row[3].isoformat() if row[3] else None,
            "end_datetime": row[4].isoformat() if row[4] else None,
            "presenter": row[5],
            "session_number": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "created_by": "admin"
        }
        for row in result
    ]

@router.delete("/{item_id}")
def delete_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_id: int
) -> Any:
    """Delete agenda item"""
    
    result = db.execute(
        text("DELETE FROM event_agenda WHERE id = :item_id AND event_id = :event_id"),
        {"item_id": item_id, "event_id": event_id}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Agenda item not found")
    
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