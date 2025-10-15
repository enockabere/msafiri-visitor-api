from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.tenant import Tenant

def get_tenant_id_from_context(db, tenant_context, current_user):
    """Helper function to get tenant ID from context"""
    if tenant_context.isdigit():
        return int(tenant_context)
    else:
        # Look up tenant by slug
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_context).first()
        return tenant.id if tenant else current_user.tenant_id

router = APIRouter()

@router.post("/room-allocations", response_model=schemas.AccommodationAllocation)
def create_room_allocation(
    allocation_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Allocate visitor to room with gender validation"""
    print(f"🏠 DEBUG: ===== ROOM ALLOCATION ENDPOINT REACHED =====")
    print(f"🏠 DEBUG: User: {current_user.email}, Tenant: {tenant_context}")
    print(f"🏠 DEBUG: Allocation data: {allocation_data}")
    
    try:
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
            print(f"🏠 DEBUG: Permission denied for role: {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
        
        # Convert dict to schema object for CRUD operation
        from app.schemas.accommodation import AccommodationAllocationCreate
        allocation_schema = AccommodationAllocationCreate(**allocation_data)
        
        allocation = crud.accommodation_allocation.create_with_tenant(
            db, obj_in=allocation_schema, tenant_id=tenant_id, user_id=current_user.id
        )
        print(f"🏠 DEBUG: ===== ALLOCATION CREATED SUCCESSFULLY: {allocation.id} =====")
        return allocation
        
    except Exception as e:
        print(f"🏠 DEBUG: Error creating allocation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating allocation: {str(e)}"
        )