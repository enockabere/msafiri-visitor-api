from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.database import get_db
from app.crud.transport_provider import transport_provider
from app.schemas.transport_provider import (
    TransportProvider,
    TransportProviderCreate,
    TransportProviderUpdate
)
from app.models.user import User

router = APIRouter()

@router.get("/tenant/{tenant_id}", response_model=List[TransportProvider])
def get_tenant_transport_providers(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get all transport providers for a tenant"""
    providers = transport_provider.get_by_tenant(db, tenant_id=tenant_id)
    return providers

@router.get("/tenant/{tenant_id}/provider/{provider_name}", response_model=TransportProvider)
def get_transport_provider(
    tenant_id: int,
    provider_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get specific transport provider configuration"""
    provider = transport_provider.get_by_tenant_and_provider(
        db, tenant_id=tenant_id, provider_name=provider_name
    )
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transport provider not found"
        )
    
    # Create response with masked secrets
    response_data = {
        "id": provider.id,
        "provider_name": provider.provider_name,
        "is_enabled": provider.is_enabled,
        "client_id": provider.client_id,
        "api_base_url": provider.api_base_url,
        "token_url": provider.token_url,
        "tenant_id": provider.tenant_id,
        "created_by": provider.created_by,
        "updated_by": provider.updated_by,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
        # Mask secrets if they exist
        "client_secret": "••••••••" if provider.client_secret else "",
        "hmac_secret": "••••••••" if provider.hmac_secret else ""
    }
    
    return response_data

@router.post("/tenant/{tenant_id}", response_model=TransportProvider)
def create_transport_provider(
    tenant_id: int,
    provider_in: TransportProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Create transport provider configuration"""
    existing = transport_provider.get_by_tenant_and_provider(
        db, tenant_id=tenant_id, provider_name=provider_in.provider_name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transport provider already configured"
        )
    
    provider = transport_provider.create_with_tenant(
        db, obj_in=provider_in, tenant_id=tenant_id, created_by=current_user.email
    )
    return provider

@router.put("/tenant/{tenant_id}/provider/{provider_name}", response_model=TransportProvider)
def update_transport_provider(
    tenant_id: int,
    provider_name: str,
    provider_in: TransportProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Update transport provider configuration"""
    provider = transport_provider.get_by_tenant_and_provider(
        db, tenant_id=tenant_id, provider_name=provider_name
    )
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transport provider not found"
        )
    
    update_data = provider_in.dict(exclude_unset=True)
    update_data["updated_by"] = current_user.email
    provider = transport_provider.update(db, db_obj=provider, obj_in=update_data)
    return provider