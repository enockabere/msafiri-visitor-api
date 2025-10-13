from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List
from app.db.database import get_db
from app.models.security_brief import SecurityBrief, UserBriefAcknowledgment, BriefType, ContentType
from app.schemas.security_brief import (
    SecurityBriefCreate, SecurityBriefUpdate, SecurityBrief as SecurityBriefSchema,
    BriefAcknowledgment, UserBriefStatus
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=dict)
def create_security_brief(
    brief: SecurityBriefCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create security brief - allow authenticated users"""
    # Map frontend fields to database model
    brief_type = BriefType.EVENT_SPECIFIC if brief.event_id else BriefType.GENERAL
    
    # Map content type
    content_type_map = {
        "text": ContentType.TEXT,
        "rich_text": ContentType.TEXT,
        "document_link": ContentType.TEXT,
        "video_link": ContentType.VIDEO
    }
    content_type = content_type_map.get(brief.content_type, ContentType.TEXT)
    
    db_brief = SecurityBrief(
        title=brief.title,
        brief_type=brief_type,
        content_type=content_type,
        content=brief.content or "",
        event_id=brief.event_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.email
    )
    db.add(db_brief)
    db.commit()
    db.refresh(db_brief)
    
    return {
        "id": db_brief.id,
        "title": db_brief.title,
        "content": db_brief.content,
        "document_url": brief.document_url,
        "video_url": brief.video_url,
        "created_by": db_brief.created_by,
        "created_at": db_brief.created_at.isoformat() if db_brief.created_at else None
    }

@router.get("/", response_model=List[dict])
def get_security_briefs(
    event_id: int = None,
    tenant: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get security briefs - general ones and event-specific if event_id provided"""
    query = db.query(SecurityBrief).filter(
        and_(
            SecurityBrief.tenant_id == current_user.tenant_id,
            SecurityBrief.is_active == True
        )
    )
    
    if event_id:
        # Get general briefs + event-specific briefs for this event
        query = query.filter(
            or_(
                SecurityBrief.brief_type == BriefType.GENERAL,
                and_(
                    SecurityBrief.brief_type == BriefType.EVENT_SPECIFIC,
                    SecurityBrief.event_id == event_id
                )
            )
        )
    else:
        # Only general briefs
        query = query.filter(SecurityBrief.brief_type == BriefType.GENERAL)
    
    briefs = query.all()
    
    return [
        {
            "id": brief.id,
            "title": brief.title,
            "type": brief.brief_type.value,
            "content_type": brief.content_type.value,
            "content": brief.content,
            "status": "published",
            "created_by": brief.created_by,
            "created_at": brief.created_at.isoformat() if brief.created_at else None
        }
        for brief in briefs
    ]

@router.get("/my-status", response_model=List[UserBriefStatus])
def get_my_brief_status(
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's acknowledgment status for security briefs"""
    # Get applicable briefs
    query = db.query(SecurityBrief).filter(
        and_(
            SecurityBrief.tenant_id == current_user.tenant_id,
            SecurityBrief.is_active == True
        )
    )
    
    if event_id:
        query = query.filter(
            or_(
                SecurityBrief.brief_type == BriefType.GENERAL,
                and_(
                    SecurityBrief.brief_type == BriefType.EVENT_SPECIFIC,
                    SecurityBrief.event_id == event_id
                )
            )
        )
    else:
        query = query.filter(SecurityBrief.brief_type == BriefType.GENERAL)
    
    briefs = query.all()
    
    # Get user's acknowledgments
    acknowledgments = db.query(UserBriefAcknowledgment).filter(
        UserBriefAcknowledgment.acknowledged_at == current_user.email
    ).all()
    
    ack_brief_ids = {ack.brief_id for ack in acknowledgments}
    
    result = []
    for brief in briefs:
        result.append(UserBriefStatus(
            brief_id=brief.id,
            title=brief.title,
            brief_type=brief.brief_type.value,
            content_type=brief.content_type.value,
            acknowledged=brief.id in ack_brief_ids,
            acknowledged_at=next((ack.created_at for ack in acknowledgments if ack.brief_id == brief.id), None)
        ))
    
    return result

@router.post("/acknowledge")
def acknowledge_brief(
    acknowledgment: BriefAcknowledgment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User acknowledges reading a security brief"""
    # Check if brief exists
    brief = db.query(SecurityBrief).filter(SecurityBrief.id == acknowledgment.brief_id).first()
    if not brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    # Check if already acknowledged
    existing = db.query(UserBriefAcknowledgment).filter(
        and_(
            UserBriefAcknowledgment.brief_id == acknowledgment.brief_id,
            UserBriefAcknowledgment.acknowledged_at == current_user.email
        )
    ).first()
    
    if existing:
        return {"message": "Brief already acknowledged"}
    
    # Create acknowledgment
    ack = UserBriefAcknowledgment(
        user_id=current_user.id,
        brief_id=acknowledgment.brief_id,
        acknowledged_at=current_user.email
    )
    db.add(ack)
    db.commit()
    
    return {"message": "Security brief acknowledged"}

@router.put("/{brief_id}", response_model=dict)
def update_security_brief(
    brief_id: int,
    brief_update: SecurityBriefUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update security brief - allow authenticated users"""
    
    db_brief = db.query(SecurityBrief).filter(SecurityBrief.id == brief_id).first()
    if not db_brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    for field, value in brief_update.dict(exclude_unset=True).items():
        setattr(db_brief, field, value)
    
    db.commit()
    db.refresh(db_brief)
    
    return {
        "id": db_brief.id,
        "title": db_brief.title,
        "content": db_brief.content,
        "document_url": db_brief.document_url,
        "video_url": db_brief.video_url,
        "created_by": db_brief.created_by,
        "created_at": db_brief.created_at.isoformat() if db_brief.created_at else None
    }

@router.delete("/{brief_id}")
def delete_security_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate security brief - allow authenticated users"""
    
    db_brief = db.query(SecurityBrief).filter(SecurityBrief.id == brief_id).first()
    if not db_brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    db_brief.is_active = False
    db.commit()
    return {"message": "Security brief deactivated"}