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
import json

router = APIRouter()

class FormFieldCreate(BaseModel):
    field_name: str
    field_label: str
    field_type: str  # text, email, select, checkbox, textarea, radio, date
    field_options: Optional[List[str]] = None
    is_required: bool = False
    order_index: int = 0
    section: Optional[str] = None  # personal, contact, travel, final
    is_protected: bool = False

class FormFieldUpdate(BaseModel):
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    field_options: Optional[List[str]] = None
    is_required: Optional[bool] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None
    section: Optional[str] = None

class FormFieldResponse(BaseModel):
    id: int
    field_name: str
    field_label: str
    field_type: str
    field_options: Optional[List[str]] = None
    is_required: bool
    order_index: int
    is_active: bool
    is_protected: bool
    section: Optional[str] = None

@router.get("/events/{event_id}/form-fields", response_model=List[FormFieldResponse])
def get_event_form_fields(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get all form fields for an event (admin endpoint)"""
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
            "is_protected": field.is_protected if hasattr(field, 'is_protected') else False,
            "section": field.section if hasattr(field, 'section') else None,
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
        order_index=field_data.order_index,
        section=field_data.section,
        is_protected=field_data.is_protected
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
    if field_data.section is not None:
        form_field.section = field_data.section

    db.commit()
    return {"message": "Form field updated successfully"}

@router.delete("/form-fields/{field_id}")
def delete_form_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a form field (soft delete)"""
    form_field = db.query(FormField).filter(FormField.id == field_id).first()
    if not form_field:
        raise HTTPException(status_code=404, detail="Form field not found")

    # Check if field is protected
    if form_field.is_protected:
        raise HTTPException(
            status_code=403,
            detail="This field is protected and cannot be deleted as it is linked to the database schema."
        )

    # Soft delete
    form_field.is_active = False
    db.commit()
    return {"message": "Form field deleted successfully"}

@router.post("/events/{event_id}/initialize-default-fields")
def initialize_default_form_fields(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initialize default form fields for an event if none exist"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if fields already exist
    existing_fields = db.query(FormField).filter(FormField.event_id == event_id).count()
    if existing_fields > 0:
        return {"message": "Form fields already exist for this event"}
    
    # Create default protected fields
    default_fields = [
        # Personal Information Section
        {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
        {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
        {"field_name": "oc", "field_label": "What is your OC?", "field_type": "select", "field_options": json.dumps(["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]), "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
        {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": json.dumps(["On contract", "Between contracts"]), "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
        {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": json.dumps(["Man", "Woman", "Non-binary", "Prefer to self-describe", "Prefer not to disclose"]), "is_required": True, "order_index": 105, "section": "personal", "is_protected": True},
        
        # Contact Details Section
        {"field_name": "personalEmail", "field_label": "Personal/Tembo Email Address", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
        {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "text", "is_required": True, "order_index": 202, "section": "contact", "is_protected": True},
        
        # Travel & Accommodation Section
        {"field_name": "travellingInternationally", "field_label": "Will you be travelling internationally?", "field_type": "select", "field_options": json.dumps(["Yes", "No"]), "is_required": True, "order_index": 301, "section": "travel"},
        {"field_name": "accommodationType", "field_label": "Accommodation Type", "field_type": "select", "field_options": json.dumps(["Staying at accommodation", "Travelling daily"]), "is_required": True, "order_index": 302, "section": "travel"},
        
        # Final Details Section
        {"field_name": "codeOfConductConfirm", "field_label": "Code of Conduct Confirmation", "field_type": "select", "field_options": json.dumps(["I agree"]), "is_required": True, "order_index": 401, "section": "final"},
    ]
    
    # Create form fields
    for field_data in default_fields:
        form_field = FormField(
            event_id=event_id,
            **field_data
        )
        db.add(form_field)
    
    db.commit()
    return {"message": f"Initialized {len(default_fields)} default form fields for event {event_id}"}
