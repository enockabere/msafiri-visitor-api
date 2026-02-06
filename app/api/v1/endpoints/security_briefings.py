from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
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
    event_check = db.execute(
        text("SELECT id FROM events WHERE id = :event_id"),
        {"event_id": event_id}
    ).fetchone()
    
    if not event_check:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create briefing using raw SQL
    result = db.execute(
        text("""
            INSERT INTO security_briefings (event_id, title, content, document_url, video_url, created_by, created_at)
            VALUES (:event_id, :title, :content, :document_url, :video_url, :created_by, CURRENT_TIMESTAMP)
            RETURNING id, created_at
        """),
        {
            "event_id": event_id,
            "title": briefing_in.title,
            "content": briefing_in.content,
            "document_url": briefing_in.document_url,
            "video_url": briefing_in.video_url,
            "created_by": "admin"
        }
    ).fetchone()
    
    db.commit()
    
    return {
        "id": result[0],
        "title": briefing_in.title,
        "content": briefing_in.content,
        "document_url": briefing_in.document_url,
        "video_url": briefing_in.video_url,
        "created_by": "admin",
        "created_at": result[1].isoformat()
    }

@router.get("/", response_model=List[dict])
def get_security_briefings(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get security briefings"""
    
    briefings = db.execute(
        text("""
            SELECT id, title, content, document_url, video_url, created_by, created_at
            FROM security_briefings 
            WHERE event_id = :event_id
            ORDER BY created_at DESC
        """),
        {"event_id": event_id}
    ).fetchall()
    
    return [
        {
            "id": briefing[0],
            "title": briefing[1],
            "content": briefing[2],
            "document_url": briefing[3],
            "video_url": briefing[4],
            "created_by": briefing[5],
            "created_at": briefing[6].isoformat() if briefing[6] else None
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
    
    result = db.execute(
        text("""
            DELETE FROM security_briefings 
            WHERE id = :briefing_id AND event_id = :event_id
        """),
        {"briefing_id": briefing_id, "event_id": event_id}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Security briefing not found")
    
    db.commit()
    return {"message": "Security briefing deleted successfully"}
