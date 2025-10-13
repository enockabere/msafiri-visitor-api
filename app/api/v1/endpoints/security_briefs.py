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

@router.patch("/{brief_id}/status", response_model=dict)
def update_brief_status(
    brief_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update security brief status"""
    
    db_brief = db.query(SecurityBrief).filter(SecurityBrief.id == brief_id).first()
    if not db_brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    new_status = status_data.get("status")
    if new_status not in ["draft", "published", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    db_brief.status = new_status
    db.commit()
    
    return {
        "id": db_brief.id,
        "status": db_brief.status,
        "message": f"Status updated to {new_status}"
    }

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
        status=brief.status or "draft",
        publish_start_date=brief.publish_start_date,
        publish_end_date=brief.publish_end_date,
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
        "status": db_brief.status,
        "publish_start_date": db_brief.publish_start_date,
        "publish_end_date": db_brief.publish_end_date,
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
            "status": brief.status or "draft",
            "publish_start_date": brief.publish_start_date,
            "publish_end_date": brief.publish_end_date,
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
    """Update security brief - only allow editing drafts"""
    
    db_brief = db.query(SecurityBrief).filter(SecurityBrief.id == brief_id).first()
    if not db_brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    # Only allow editing drafts
    if db_brief.status != "draft":
        raise HTTPException(status_code=403, detail="Can only edit draft briefings")
    
    # Map frontend fields
    update_data = brief_update.dict(exclude_unset=True)
    if "type" in update_data:
        update_data["brief_type"] = BriefType.EVENT_SPECIFIC if update_data.get("event_id") else BriefType.GENERAL
        del update_data["type"]
    
    for field, value in update_data.items():
        if hasattr(db_brief, field):
            setattr(db_brief, field, value)
    
    db.commit()
    db.refresh(db_brief)
    
    return {
        "id": db_brief.id,
        "title": db_brief.title,
        "content": db_brief.content,
        "status": db_brief.status,
        "publish_start_date": db_brief.publish_start_date,
        "publish_end_date": db_brief.publish_end_date,
        "created_by": db_brief.created_by,
        "created_at": db_brief.created_at.isoformat() if db_brief.created_at else None
    }

@router.delete("/{brief_id}")
def delete_security_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete security brief - only allow deleting drafts"""
    
    db_brief = db.query(SecurityBrief).filter(SecurityBrief.id == brief_id).first()
    if not db_brief:
        raise HTTPException(status_code=404, detail="Security brief not found")
    
    # Only allow deleting drafts
    if db_brief.status != "draft":
        raise HTTPException(status_code=403, detail="Can only delete draft briefings")
    
    db.delete(db_brief)
    db.commit()
    return {"message": "Security brief deleted successfully"}