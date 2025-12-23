from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os

from app.db.database import get_db
from app.core.deps import get_current_active_user
from app.crud.badge_template import badge_template
from app.schemas.badge_template import BadgeTemplate, BadgeTemplateCreate, BadgeTemplateUpdate
from app.models.user import User
from app.models.event_participant import EventParticipant

router = APIRouter()

@router.get("/", response_model=dict)
def get_badge_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    Retrieve badge templates.
    """
    try:
        templates = badge_template.get_multi(db, skip=skip, limit=limit)
        template_list = []
        for template in templates:
            print(f"[BADGE] Template: '{template.name}' - Status: {'ACTIVE' if template.is_active else 'INACTIVE'}")
            
            template_dict = {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "template_content": template.template_content,
                "logo_url": template.logo_url,
                "logo_public_id": template.logo_public_id,
                "background_url": template.background_url,
                "background_public_id": template.background_public_id,
                "enable_qr_code": template.enable_qr_code,
                "is_active": template.is_active,
                "badge_size": template.badge_size,
                "orientation": template.orientation,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
            template_list.append(template_dict)
        
        print(f"[BADGE] Total templates found: {len(template_list)}")
        return {"templates": template_list}
    except Exception as e:
        print(f"Error loading badge templates: {e}")
        return {"templates": []}

@router.post("/", response_model=BadgeTemplate)
def create_badge_template(
    *,
    db: Session = Depends(get_db),
    template_in: BadgeTemplateCreate,
    current_user: User = Depends(get_current_active_user),
) -> BadgeTemplate:
    """
    Create new badge template.
    """
    existing_template = badge_template.get_by_name(db, name=template_in.name)
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )
    
    template = badge_template.create(db=db, obj_in=template_in)
    return template

@router.get("/{template_id}", response_model=BadgeTemplate)
def get_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
) -> BadgeTemplate:
    """
    Get badge template by ID.
    """
    template = badge_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    return template

@router.put("/{template_id}", response_model=BadgeTemplate)
def update_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    template_in: BadgeTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
) -> BadgeTemplate:
    """
    Update badge template.
    """
    template = badge_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    template = badge_template.update(db=db, db_obj=template, obj_in=template_in)
    return template

@router.delete("/{template_id}")
def delete_badge_template(
    *,
    db: Session = Depends(get_db),
    template_id: int,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Delete badge template.
    """
    template = badge_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    badge_template.remove(db=db, id=template_id)
    return {"message": "Template deleted successfully"}

@router.get("/active/list", response_model=List[BadgeTemplate])
def get_active_badge_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[BadgeTemplate]:
    """
    Get all active badge templates.
    """
    return badge_template.get_active_templates(db)