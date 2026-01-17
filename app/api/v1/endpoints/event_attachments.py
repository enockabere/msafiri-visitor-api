from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_attachment import EventAttachment
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader
import os

router = APIRouter()

class AttachmentCreate(BaseModel):
    name: str
    url: str
    description: str = None
    public_id: str = None
    file_type: str = None
    resource_type: str = None
    original_filename: str = None

@router.post("/", response_model=dict, operation_id="create_event_attachment_unique")
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
        public_id=attachment_in.public_id,
        file_type=attachment_in.file_type,
        resource_type=attachment_in.resource_type,
        original_filename=attachment_in.original_filename,
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
        "public_id": attachment.public_id,
        "file_type": attachment.file_type,
        "resource_type": attachment.resource_type,
        "original_filename": attachment.original_filename,
        "created_at": attachment.created_at.isoformat()
    }

@router.get("/", response_model=List[dict], operation_id="get_event_attachments_unique")
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
            "public_id": att.public_id,
            "file_type": att.file_type,
            "resource_type": att.resource_type,
            "original_filename": att.original_filename,
            "created_at": att.created_at.isoformat()
        }
        for att in attachments
    ]



@router.delete("/{attachment_id}/", operation_id="delete_event_attachment_unique")
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
    
    # Delete from Cloudinary if public_id exists
    if attachment.public_id:
        try:
            resource_type = attachment.resource_type or "raw"
            cloudinary.uploader.destroy(attachment.public_id, resource_type=resource_type)
        except Exception as e:
            print(f"Warning: Failed to delete from Cloudinary: {str(e)}")
    
    # Delete database record
    db.delete(attachment)
    db.commit()
    
    return {"message": "Attachment deleted successfully"}