"""
Service for creating default roles when a tenant is created
"""
from sqlalchemy.orm import Session
from app import crud, schemas
import logging

logger = logging.getLogger(__name__)

def create_default_roles_for_tenant(db: Session, tenant_slug: str) -> None:
    """Create default roles for a new tenant"""
    
    default_roles = [
        ("MT Admin", "Movement and Travel Administrator"),
        ("HR Admin", "Human Resources Administrator"), 
        ("Event Admin", "Event Administrator"),
        ("Finance Admin", "Finance Administrator"),
        ("Staff", "Staff Member"),
        ("Guest", "Guest User")
    ]
    
    try:
        for role_name, role_description in default_roles:
            # Check if role already exists
            existing_role = crud.role.get_by_name_and_tenant(
                db, name=role_name, tenant_id=tenant_slug
            )
            
            if not existing_role:
                # Create the role
                role_data = schemas.RoleCreate(
                    name=role_name,
                    description=role_description,
                    tenant_id=tenant_slug,
                    is_active=True
                )
                
                role = crud.role.create(db, obj_in=role_data)
                logger.info(f"Created default role '{role_name}' for tenant '{tenant_slug}'")
            else:
                logger.info(f"Role '{role_name}' already exists for tenant '{tenant_slug}'")
                
    except Exception as e:
        logger.error(f"Failed to create default roles for tenant '{tenant_slug}': {e}")
        raise