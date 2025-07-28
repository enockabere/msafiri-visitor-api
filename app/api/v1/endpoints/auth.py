from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.database import get_db

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # For multi-tenant, we can extract tenant from username like: user@tenant
    # Or use a separate tenant field
    email_parts = form_data.username.split("@")
    if len(email_parts) > 2:  # Format: user@domain@tenant
        email = "@".join(email_parts[:-1])
        tenant_slug = email_parts[-1]
        
        # Get tenant by slug
        tenant = crud.tenant.get_by_slug(db, slug=tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
        tenant_id = tenant.slug
    else:
        email = form_data.username
        tenant_id = None

    user = crud.user.authenticate(
        db, email=email, password=form_data.password, tenant_id=tenant_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/login/tenant", response_model=schemas.Token)
def login_with_tenant(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with explicit tenant specification
    """
    tenant_id = None
    if login_data.tenant_slug:
        tenant = crud.tenant.get_by_slug(db, slug=login_data.tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
        tenant_id = tenant.slug

    user = crud.user.authenticate(
        db, email=login_data.email, password=login_data.password, tenant_id=tenant_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: schemas.User = Depends(deps.get_current_user)) -> Any:
    """
    Test access token
    """
    return current_user