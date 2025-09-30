from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_attachment import EventAttachment
from pydantic import BaseModel

router = APIRouter()

class AttachmentCreate(BaseModel):
    name: str
    url: str
    description: str = None

@router.post("/", response_model=dict, operation_id="create_event_attachment")
def create_attachment(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    attachment_in: AttachmentCreate
) -> Any:
    """Create event attachment"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create attachment
    attachment = EventAttachment(
        event_id=event_id,
        name=attachment_in.name,
        url=attachment_in.url,
        description=attachment_in.description,
        uploaded_by='admin'
    )
    
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    return {
        "id": attachment.id,
        "name": attachment.name,
        "url": attachment.url,
        "description": attachment.description,
        "uploaded_by": attachment.uploaded_by,
        "created_at": attachment.created_at.isoformat()
    }

@router.get("/", response_model=List[dict], operation_id="get_event_attachments")
def get_attachments(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get event attachments"""
    
    attachments = db.query(EventAttachment).filter(
        EventAttachment.event_id == event_id
    ).all()
    
    return [
        {
            "id": att.id,
            "name": att.name,
            "url": att.url,
            "description": att.description,
            "uploaded_by": att.uploaded_by,
            "created_at": att.created_at.isoformat()
        }
        for att in attachments
    ]



@router.delete("/{attachment_id}/", operation_id="delete_event_attachment")
def delete_attachment(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    attachment_id: int
) -> Any:
    """Delete event attachment"""
    
    attachment = db.query(EventAttachment).filter(
        EventAttachment.id == attachment_id,
        EventAttachment.event_id == event_id
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Delete database record
    db.delete(attachment)
    db.commit()
    
    return {"message": "Attachment deleted successfully"}