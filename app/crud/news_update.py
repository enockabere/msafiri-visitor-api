from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.models.news_update import NewsUpdate
from app.schemas.news_update import NewsUpdateCreate, NewsUpdateUpdate
from datetime import datetime

def create_news_update(
    db: Session, 
    news_update: NewsUpdateCreate, 
    tenant_id: int, 
    created_by: str
) -> NewsUpdate:
    news_data = news_update.dict()
    
    # Set published_at if publishing immediately
    if news_data.get('is_published', False):
        news_data['published_at'] = datetime.utcnow()
    
    db_news_update = NewsUpdate(
        **news_data,
        tenant_id=tenant_id,
        created_by=created_by
    )
    db.add(db_news_update)
    db.commit()
    db.refresh(db_news_update)
    return db_news_update

def get_news_update(db: Session, news_update_id: int, tenant_id: int) -> Optional[NewsUpdate]:
    return db.query(NewsUpdate).filter(
        and_(NewsUpdate.id == news_update_id, NewsUpdate.tenant_id == tenant_id)
    ).first()

def get_news_updates(
    db: Session, 
    tenant_id: int, 
    skip: int = 0, 
    limit: int = 100,
    published_only: bool = False
) -> List[NewsUpdate]:
    query = db.query(NewsUpdate).filter(NewsUpdate.tenant_id == tenant_id)
    
    if published_only:
        query = query.filter(NewsUpdate.is_published == True)
    
    return query.order_by(desc(NewsUpdate.created_at)).offset(skip).limit(limit).all()

def get_news_updates_count(db: Session, tenant_id: int, published_only: bool = False) -> int:
    query = db.query(NewsUpdate).filter(NewsUpdate.tenant_id == tenant_id)
    
    if published_only:
        query = query.filter(NewsUpdate.is_published == True)
    
    return query.count()

def update_news_update(
    db: Session, 
    news_update_id: int, 
    tenant_id: int, 
    news_update_update: NewsUpdateUpdate
) -> Optional[NewsUpdate]:
    db_news_update = get_news_update(db, news_update_id, tenant_id)
    if not db_news_update:
        return None
    
    update_data = news_update_update.dict(exclude_unset=True)
    
    # Handle publishing logic
    if 'is_published' in update_data and update_data['is_published']:
        if not db_news_update.published_at:
            update_data['published_at'] = datetime.utcnow()
    elif 'is_published' in update_data and not update_data['is_published']:
        update_data['published_at'] = None
    
    for field, value in update_data.items():
        setattr(db_news_update, field, value)
    
    db.commit()
    db.refresh(db_news_update)
    return db_news_update

def publish_news_update(
    db: Session, 
    news_update_id: int, 
    tenant_id: int, 
    is_published: bool
) -> Optional[NewsUpdate]:
    db_news_update = get_news_update(db, news_update_id, tenant_id)
    if not db_news_update:
        return None
    
    db_news_update.is_published = is_published
    if is_published and not db_news_update.published_at:
        db_news_update.published_at = datetime.utcnow()
    elif not is_published:
        db_news_update.published_at = None
    
    db.commit()
    db.refresh(db_news_update)
    return db_news_update

def delete_news_update(db: Session, news_update_id: int, tenant_id: int) -> bool:
    db_news_update = get_news_update(db, news_update_id, tenant_id)
    if not db_news_update:
        return False
    
    db.delete(db_news_update)
    db.commit()
    return True

def get_published_news_for_mobile(
    db: Session, 
    tenant_id: int, 
    skip: int = 0, 
    limit: int = 20
) -> List[NewsUpdate]:
    """Get published news updates for mobile app"""
    return db.query(NewsUpdate).filter(
        and_(
            NewsUpdate.tenant_id == tenant_id,
            NewsUpdate.is_published == True
        )
    ).order_by(desc(NewsUpdate.published_at)).offset(skip).limit(limit).all()