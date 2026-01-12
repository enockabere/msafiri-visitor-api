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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

@router.get("/event/{event_id}/responses")
def get_event_form_responses(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all form responses for an event with field details"""
    # Get form responses with field information
    responses = db.query(
        FormResponse.id,
        FormResponse.field_id,
        FormResponse.registration_id,
        FormResponse.field_value,
        FormField.field_name,
        FormField.field_label
    ).join(FormField).filter(
        FormField.event_id == event_id
    ).all()
    
    return [{
        "id": r.id, 
        "field_id": r.field_id, 
        "registration_id": r.registration_id, 
        "field_value": r.field_value,
        "field_name": r.field_name,
        "field_label": r.field_label
    } for r in responses]

@router.post("/events/{event_id}/restore-complete-fields")
def restore_complete_form_fields(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore complete set of form fields including missing important ones"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Complete list of all important fields
    complete_fields = [
        # Personal Information Section
        {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
        {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
        {"field_name": "oc", "field_label": "What is your OC?", "field_type": "select", "field_options": json.dumps(["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]), "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
        {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": json.dumps(["On contract", "Between contracts"]), "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
        {"field_name": "contractType", "field_label": "Contract Type", "field_type": "select", "field_options": json.dumps(["International", "National"]), "is_required": False, "order_index": 105, "section": "personal"},
        {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": json.dumps(["Man", "Woman", "Non-binary", "Prefer to self-describe", "Prefer not to disclose"]), "is_required": True, "order_index": 106, "section": "personal", "is_protected": True},
        {"field_name": "sex", "field_label": "Sex", "field_type": "select", "field_options": json.dumps(["Male", "Female", "Prefer not to disclose"]), "is_required": False, "order_index": 107, "section": "personal"},
        {"field_name": "pronouns", "field_label": "Pronouns", "field_type": "text", "is_required": False, "order_index": 108, "section": "personal"},
        {"field_name": "nationality", "field_label": "What is your nationality?", "field_type": "select", "field_options": json.dumps(["API_COUNTRIES"]), "is_required": False, "order_index": 109, "section": "personal"},
        {"field_name": "currentPosition", "field_label": "Current Position", "field_type": "text", "is_required": False, "order_index": 110, "section": "personal"},
        {"field_name": "countryOfWork", "field_label": "Country of Work", "field_type": "select", "field_options": json.dumps(["API_COUNTRIES"]), "is_required": False, "order_index": 111, "section": "personal"},
        {"field_name": "projectOfWork", "field_label": "Project of Work", "field_type": "text", "is_required": False, "order_index": 112, "section": "personal"},
        
        # Contact Details Section
        {"field_name": "personalEmail", "field_label": "Personal/Tembo Email Address", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
        {"field_name": "msfEmail", "field_label": "MSF Email Address", "field_type": "email", "is_required": False, "order_index": 202, "section": "contact"},
        {"field_name": "hrcoEmail", "field_label": "HRCO Email Address", "field_type": "email", "is_required": False, "order_index": 203, "section": "contact"},
        {"field_name": "careerManagerEmail", "field_label": "Career Manager Email", "field_type": "email", "is_required": False, "order_index": 204, "section": "contact"},
        {"field_name": "lineManagerEmail", "field_label": "Line Manager Email", "field_type": "email", "is_required": False, "order_index": 205, "section": "contact"},
        {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "phone", "is_required": True, "order_index": 206, "section": "contact", "is_protected": True},
        
        # Travel & Accommodation Section
        {"field_name": "travellingInternationally", "field_label": "Will you be travelling internationally?", "field_type": "select", "field_options": json.dumps(["Yes", "No"]), "is_required": True, "order_index": 301, "section": "travel"},
        {"field_name": "travellingFromCountry", "field_label": "Travelling From Country", "field_type": "text", "is_required": False, "order_index": 302, "section": "travel"},
        {"field_name": "accommodationType", "field_label": "Accommodation Type", "field_type": "select", "field_options": json.dumps(["Staying at accommodation", "Travelling daily"]), "is_required": True, "order_index": 303, "section": "travel"},
        {"field_name": "dietaryRequirements", "field_label": "Dietary Requirements", "field_type": "textarea", "is_required": False, "order_index": 304, "section": "travel"},
        {"field_name": "accommodationNeeds", "field_label": "Accommodation Needs", "field_type": "textarea", "is_required": False, "order_index": 305, "section": "travel"},
        
        # Final Details Section
        {"field_name": "certificateName", "field_label": "Certificate Name", "field_type": "text", "is_required": False, "order_index": 401, "section": "final"},
        {"field_name": "badgeName", "field_label": "Badge Name", "field_type": "text", "is_required": False, "order_index": 402, "section": "final"},
        {"field_name": "motivationLetter", "field_label": "Motivation Letter", "field_type": "richtext", "is_required": False, "order_index": 403, "section": "final"},
        {"field_name": "codeOfConductConfirm", "field_label": "Code of Conduct Confirmation", "field_type": "select", "field_options": json.dumps(["I agree"]), "is_required": True, "order_index": 404, "section": "final"},
    ]
    
    # Get existing field names
    existing_field_names = set(
        field.field_name for field in db.query(FormField).filter(FormField.event_id == event_id).all()
    )
    
    # Only create missing fields
    missing_fields = [
        field_data for field_data in complete_fields 
        if field_data["field_name"] not in existing_field_names
    ]
    
    # Create missing fields
    created_count = 0
    for field_data in missing_fields:
        form_field = FormField(
            event_id=event_id,
            **field_data
        )
        db.add(form_field)
        created_count += 1
    
    db.commit()
    
    return {
        "message": f"Restored {created_count} missing form fields",
        "created_count": created_count,
        "total_fields": len(existing_field_names) + created_count
    }

@router.post("/events/{event_id}/remove-duplicates")
def remove_duplicate_form_fields(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove duplicate form fields for an event, keeping only the first occurrence of each field_name"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get all fields for this event
    all_fields = db.query(FormField).filter(
        FormField.event_id == event_id
    ).order_by(FormField.id).all()
    
    # Track seen field names and duplicates to delete
    seen_field_names = set()
    duplicates_to_delete = []
    
    for field in all_fields:
        if field.field_name in seen_field_names:
            duplicates_to_delete.append(field)
        else:
            seen_field_names.add(field.field_name)
    
    # Delete duplicates
    deleted_count = 0
    for duplicate in duplicates_to_delete:
        db.delete(duplicate)
        deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Removed {deleted_count} duplicate form fields",
        "deleted_count": deleted_count,
        "remaining_fields": len(seen_field_names)
    }

@router.post("/events/{event_id}/update-country-fields")
def update_country_fields_to_api(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update existing nationality and country fields to use countries API"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    updated_fields = []
    
    # Update nationality field
    nationality_field = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.field_name == "nationality",
        FormField.is_active == True
    ).first()
    
    if nationality_field:
        print(f"🔄 Updating nationality field: {nationality_field.field_type} -> select")
        nationality_field.field_label = "What is your nationality?"
        nationality_field.field_type = "select"
        nationality_field.field_options = json.dumps(["API_COUNTRIES"])
        updated_fields.append("nationality")
        print(f"✅ Updated nationality field to: {nationality_field.field_type}")
    
    # Update country of work field
    country_work_field = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.field_name == "countryOfWork",
        FormField.is_active == True
    ).first()
    
    if country_work_field:
        print(f"🔄 Updating countryOfWork field: {country_work_field.field_type} -> select")
        country_work_field.field_label = "Country of Work"
        country_work_field.field_type = "select"
        country_work_field.field_options = json.dumps(["API_COUNTRIES"])
        updated_fields.append("countryOfWork")
        print(f"✅ Updated countryOfWork field to: {country_work_field.field_type}")
    
    # Update travelling from country field
    travelling_from_field = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.field_name == "travellingFromCountry",
        FormField.is_active == True
    ).first()
    
    if travelling_from_field:
        print(f"🔄 Updating travellingFromCountry field: {travelling_from_field.field_type} -> select")
        travelling_from_field.field_label = "What is your nationality?"
        travelling_from_field.field_type = "select"
        travelling_from_field.field_options = json.dumps(["API_COUNTRIES"])
        updated_fields.append("travellingFromCountry")
        print(f"✅ Updated travellingFromCountry field to: {travelling_from_field.field_type}")
    
    db.commit()
    print(f"💾 Database committed. Updated fields: {updated_fields}")
    
    return {
        "message": f"Updated {len(updated_fields)} country fields to use API",
        "updated_fields": updated_fields
    }
@router.post("/events/{event_id}/update-phone-fields")
def update_phone_fields_to_phone_type(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update existing phone number fields to use phone input type"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    updated_fields = []
    
    # Update phone number field
    phone_field = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.field_name == "phoneNumber",
        FormField.is_active == True
    ).first()
    
    if phone_field:
        print(f"🔄 Updating phoneNumber field: {phone_field.field_type} -> phone")
        phone_field.field_label = "Phone Number"
        phone_field.field_type = "phone"
        phone_field.field_options = None  # Phone fields don't need options
        updated_fields.append("phoneNumber")
        print(f"✅ Updated phoneNumber field to: {phone_field.field_type}")
    
    db.commit()
    print(f"💾 Database committed. Updated fields: {updated_fields}")
    
    return {
        "message": f"Updated {len(updated_fields)} phone fields to use phone input type",
        "updated_fields": updated_fields
    }

@router.post("/events/{event_id}/initialize-default-fields")
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initialize default form fields for an event if none exist"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if fields already exist (including inactive ones to prevent duplicates)
    existing_fields = db.query(FormField).filter(FormField.event_id == event_id).count()
    if existing_fields > 0:
        return {"message": "Form fields already exist for this event"}
    
    # Double-check for any protected fields to prevent duplicates
    protected_fields = db.query(FormField).filter(
        FormField.event_id == event_id,
        FormField.is_protected == True
    ).count()
    if protected_fields > 0:
        return {"message": "Protected form fields already exist for this event"}
    
    # Create default protected fields (remove duplicates from the list)
    default_fields = [
        # Personal Information Section
        {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
        {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
        {"field_name": "oc", "field_label": "What is your OC?", "field_type": "select", "field_options": json.dumps(["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]), "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
        {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": json.dumps(["On contract", "Between contracts"]), "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
        {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": json.dumps(["Man", "Woman", "Non-binary", "Prefer to self-describe", "Prefer not to disclose"]), "is_required": True, "order_index": 105, "section": "personal", "is_protected": True},
        
        # Contact Details Section
        {"field_name": "personalEmail", "field_label": "Personal/Tembo Email Address", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
        {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "phone", "is_required": True, "order_index": 202, "section": "contact", "is_protected": True},
        
        # Travel & Accommodation Section
        {"field_name": "travellingInternationally", "field_label": "Will you be travelling internationally?", "field_type": "select", "field_options": json.dumps(["Yes", "No"]), "is_required": True, "order_index": 301, "section": "travel"},
        {"field_name": "accommodationType", "field_label": "Accommodation Type", "field_type": "select", "field_options": json.dumps(["Staying at accommodation", "Travelling daily"]), "is_required": True, "order_index": 302, "section": "travel"},
        
        # Final Details Section
        {"field_name": "codeOfConductConfirm", "field_label": "Code of Conduct Confirmation", "field_type": "select", "field_options": json.dumps(["I agree"]), "is_required": True, "order_index": 401, "section": "final"},
    ]
    
    # Check for existing fields by field_name to prevent duplicates
    existing_field_names = set(
        field.field_name for field in db.query(FormField).filter(FormField.event_id == event_id).all()
    )
    
    # Only create fields that don't already exist
    fields_to_create = [
        field_data for field_data in default_fields 
        if field_data["field_name"] not in existing_field_names
    ]
    
    if not fields_to_create:
        return {"message": "All default form fields already exist for this event"}
    
    # Create form fields
    for field_data in fields_to_create:
        form_field = FormField(
            event_id=event_id,
            **field_data
        )
        db.add(form_field)
    
    db.commit()
    return {"message": f"Initialized {len(fields_to_create)} default form fields for event {event_id}"}
