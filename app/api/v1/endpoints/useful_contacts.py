from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
import logging

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/test")
def test_endpoint():

    return {"message": "Useful contacts endpoint is working"}

@router.get("/", response_model=List[schemas.UsefulContact])
def get_contacts(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Get all useful contacts for tenant"""
    contacts = crud.useful_contact.get_by_tenant(db, tenant_id=tenant_context)
    
    return contacts

@router.get("/mobile")
def get_contacts_for_mobile(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get useful contacts for mobile app based on user's event participation"""
    from app.models.event_participant import EventParticipant
    from app.models.event import Event
    from app.models.useful_contact import UsefulContact
    from app.models.tenant import Tenant
    from datetime import datetime, timedelta
    from sqlalchemy import and_
    
    # Get user's active event participations
    active_participations = db.query(EventParticipant).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        and_(
            EventParticipant.email == current_user.email,
            EventParticipant.status.in_(['selected', 'confirmed', 'approved']),
            Event.end_date >= (datetime.now().date() - timedelta(days=30))
        )
    ).all()
    

    
    if not active_participations:

        
        return []
    
    # Get unique tenant IDs from user's events
    tenant_ids = list(set([p.event.tenant_id for p in active_participations]))

    
    # Convert tenant IDs to strings for matching (since contact tenant_id is varchar)
    tenant_id_strings = [str(tid) for tid in tenant_ids]
    
    # Also get tenant slugs since contacts might be stored with slugs instead of numeric IDs
    tenant_slugs = []
    for tenant_id in tenant_ids:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.slug:
            tenant_slugs.append(tenant.slug)
    
    # Combine both numeric IDs and slugs for matching
    all_tenant_identifiers = tenant_id_strings + tenant_slugs
    

    
    # Use string matching for both numeric IDs and slugs
    contacts = db.query(UsefulContact).filter(
        UsefulContact.tenant_id.in_(all_tenant_identifiers)
    ).all()
    

    
    # Get tenant names for display - build mapping for both IDs and slugs
    tenant_names = {}
    
    # First, map numeric IDs to names
    for tenant_id in tenant_ids:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            tenant_names[str(tenant_id)] = tenant.name
            # Also map the slug to the same name
            if tenant.slug:
                tenant_names[tenant.slug] = tenant.name

    
    # Also check if any contacts have tenant_ids that are slugs we haven't mapped yet
    for contact in contacts:
        if contact.tenant_id and contact.tenant_id not in tenant_names:
            # Try to find tenant by slug
            tenant = db.query(Tenant).filter(Tenant.slug == contact.tenant_id).first()
            if tenant:
                tenant_names[contact.tenant_id] = tenant.name

    
    # Return contacts with tenant information
    enhanced_contacts = []
    for contact in contacts:
        # Get tenant name for this contact
        tenant_name = "Unknown"
        if contact.tenant_id:
            tenant_name = tenant_names.get(contact.tenant_id, "Unknown")
        
        contact_dict = {
            "id": contact.id,
            "tenant_id": contact.tenant_id,
            "tenant_name": tenant_name,
            "name": contact.name,
            "position": contact.position,
            "email": contact.email,
            "phone": contact.phone,
            "department": contact.department,
            "availability_schedule": contact.availability_schedule,
            "availability_details": contact.availability_details,
            "created_at": contact.created_at,
            "updated_at": contact.updated_at,
            "created_by": contact.created_by
        }
        enhanced_contacts.append(contact_dict)
    

    return enhanced_contacts

@router.post("/debug")
def create_contact_debug(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
):
    """Debug endpoint to test without schema validation"""

    return {"status": "debug success", "data": request_data}

@router.post("/", response_model=schemas.UsefulContact)
def create_contact(
    *,
    db: Session = Depends(get_db),
    contact_in: schemas.UsefulContactCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Create new useful contact"""

    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        contact = crud.useful_contact.create_with_tenant(
            db, obj_in=contact_in, tenant_id=tenant_context, created_by=current_user.email
        )

        return contact
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create contact: {str(e)}"
        )

@router.put("/{contact_id}", response_model=schemas.UsefulContact)
def update_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: int,
    contact_in: schemas.UsefulContactUpdate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Update useful contact"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    contact = crud.useful_contact.get(db, id=contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    contact = crud.useful_contact.update(db, db_obj=contact, obj_in=contact_in)
    return contact

@router.delete("/{contact_id}")
def delete_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Delete useful contact"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    contact = crud.useful_contact.get(db, id=contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    
    crud.useful_contact.remove(db, id=contact_id)
    return {"message": "Contact deleted successfully"}
