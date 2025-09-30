from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.db.database import get_db
from app.models.security_briefing import SecurityBriefing
from pydantic import BaseModel

router = APIRouter()

class SecurityBriefingCreate(BaseModel):
    title: str
    content: str = None
    document_url: str = None
    video_url: str = None

@router.post("/", response_model=dict)
def create_security_briefing(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    briefing_in: SecurityBriefingCreate
) -> Any:
    """Create security briefing"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create briefing
    briefing = SecurityBriefing(
        event_id=event_id,
        title=briefing_in.title,
        content=briefing_in.content,
        document_url=briefing_in.document_url,
        video_url=briefing_in.video_url,
        created_by='admin'
    )
    
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    
    return {
        "id": briefing.id,
        "title": briefing.title,
        "content": briefing.content,
        "document_url": briefing.document_url,
        "video_url": briefing.video_url,
        "created_by": briefing.created_by,
        "created_at": briefing.created_at.isoformat()
    }

@router.get("/", response_model=List[dict])
def get_security_briefings(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get security briefings"""
    
    briefings = db.query(SecurityBriefing).filter(
        SecurityBriefing.event_id == event_id
    ).all()
    
    return [
        {
            "id": briefing.id,
            "title": briefing.title,
            "content": briefing.content,
            "document_url": briefing.document_url,
            "video_url": briefing.video_url,
            "created_by": briefing.created_by,
            "created_at": briefing.created_at.isoformat()
        }
        for briefing in briefings
    ]

@router.delete("/{briefing_id}/")
def delete_security_briefing(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    briefing_id: int
) -> Any:
    """Delete security briefing"""
    
    briefing = db.query(SecurityBriefing).filter(
        SecurityBriefing.id == briefing_id,
        SecurityBriefing.event_id == event_id
    ).first()
    
    if not briefing:
        raise HTTPException(status_code=404, detail="Security briefing not found")
    
    db.delete(briefing)
    db.commit()
    
    return {"message": "Security briefing deleted successfully"}