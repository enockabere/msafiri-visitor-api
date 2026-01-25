from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.db.database import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import TokenData

security = HTTPBearer()

def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
        
    email: str = payload.get("sub")
    tenant_id: Optional[str] = payload.get("tenant_id")
    
    if email is None:
        raise credentials_exception
        
    token_data = TokenData(email=email, tenant_id=tenant_id)
    
    # First, try to find user by email only
    user = db.query(User).filter(User.email == token_data.email).first()
    
    if user is None:
        raise credentials_exception
    
    # For super admins, don't restrict by tenant_id
    if user.role.value == "super_admin":
        return user
    
    # For other users, validate tenant_id if present in token
    if tenant_id and user.tenant_id != tenant_id:
        raise credentials_exception
    
    return user

def get_current_user_allow_expired(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current user even if token is expired (for token refresh).
    Allows recently expired tokens (within 24 hours) to be refreshed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        # Decode token without verifying expiration
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}  # Don't verify expiration for refresh
        )
    except JWTError:
        raise credentials_exception

    email: str = payload.get("sub")
    tenant_id: Optional[str] = payload.get("tenant_id")

    if email is None:
        raise credentials_exception

    token_data = TokenData(email=email, tenant_id=tenant_id)

    # Find user by email
    user = db.query(User).filter(User.email == token_data.email).first()

    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # For super admins, don't restrict by tenant_id
    if user.role.value == "super_admin":
        return user

    # For other users, validate tenant_id if present in token
    if tenant_id and user.tenant_id != tenant_id:
        raise credentials_exception

    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_tenant_context(
    x_tenant_id: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user)
) -> str:
    """
    Get tenant context from either header or user's token.
    Header takes precedence when available.
    """

    
    # Always use header tenant_id if provided (for any user)
    if x_tenant_id:

        return x_tenant_id
    
    # Fallback to user's tenant_id if available
    if current_user.tenant_id:

        return current_user.tenant_id
    

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No tenant context available"
    )