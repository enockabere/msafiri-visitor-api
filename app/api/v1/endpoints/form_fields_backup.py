from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.form_field import FormField, FormResponse
from app.models.event import Event

router = APIRouter()

class FormFieldCreate(BaseModel):
    field_name: str
    field_label: str
    field_type: str  # text, email, select, checkbox, textarea
    field_options: Optional[List[str]] = None
    is_required: bool = False
    order_index: int = 0

class FormFieldUpdate(BaseModel):
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    field_options: Optional[List[str]] = None
    is_required: Optional[bool] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class FormFieldResponse(BaseModel):
    id: int
    field_name: str
    field_label: str
    field_type: str
    field_options: Optional[List[str]] = None
    is_required: bool
    order_index: int
    is_active: bool

@router.get("/events/{event_id}/form-fields", response_model=List[FormFieldResponse])
def get_event_form_fields(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get all form fields for an event"""
    fields = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.is_active == True
    ).order_by(FormField.order_index).all()
    
    result = []
    for field in fields:
        field_data = {
            "id": field.id,
            "field_name": field.field_name,
            "field_label": field.field_label,
            "field_type": field.field_type,
            "is_required": field.is_required,
            "order_index": field.order_index,
            "is_active": field.is_active,
            "field_options": json.loads(field.field_options) if field.field_options else None
        }
        result.append(field_data)
    
    return result

@router.post("/events/{event_id}/form-fields")
def create_form_field(
    event_id: int,
    field_data: FormFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new form field for an event"""
    # Check if event exists and user has permission
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create form field
    form_field = FormField(
        event_id=event_id,
        field_name=field_data.field_name,
        field_label=field_data.field_label,
        field_type=field_data.field_type,
        field_options=json.dumps(field_data.field_options) if field_data.field_options else None,
        is_required=field_data.is_required,
        order_index=field_data.order_index
    )
    
    db.add(form_field)
    db.commit()
    db.refresh(form_field)
    
    return {"message": "Form field created successfully", "field_id": form_field.id}

@router.put("/form-fields/{field_id}")
def update_form_field(
    field_id: int,
    field_data: FormFieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a form field"""
    form_field = db.query(FormField).filter(FormField.id == field_id).first()
    if not form_field:
        raise HTTPException(status_code=404, detail="Form field not found")
    
    # Update fields
    if field_data.field_label is not None:
        form_field.field_label = field_data.field_label
    if field_data.field_type is not None:
        form_field.field_type = field_data.field_type
    if field_data.field_options is not None:
        form_field.field_options = json.dumps(field_data.field_options)
    if field_data.is_required is not None:
        form_field.is_required = field_data.is_required
    if field_data.order_index is not None:
        form_field.order_index = field_data.order_index
    if field_data.is_active is not None:
        form_field.is_active = field_data.is_active
    
    db.commit()
    return {"message": "Form field updated successfully"}

@router.delete("/form-fields/{field_id}")
def delete_form_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a form field"""
    form_field = db.query(FormField).filter(FormField.id == field_id).first()
    if not form_field:
        raise HTTPException(status_code=404, detail="Form field not found")
    
    form_field.is_active = False
    db.commit()
    return {"message": "Form field deleted successfully"}
