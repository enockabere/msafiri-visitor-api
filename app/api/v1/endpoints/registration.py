from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.db.database import get_db
from app.models.user import UserRole, UserStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=schemas.UserRegistrationResponse)
def register_user(
    user_data: schemas.UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> schemas.UserRegistrationResponse:
    """Register a new user"""
    
    # Check if user already exists
    existing_user = crud.user.get_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate tenant if provided
    tenant_id = None
    if user_data.tenant_slug:
        tenant = crud.tenant.get_by_slug(db, slug=user_data.tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization code"
            )
        tenant_id = tenant.slug
    
    try:
        # Create user with GUEST role by default - mobile users can access all tenants
        user_create = schemas.UserCreate(
            email=user_data.email,
            full_name=user_data.full_name,
            phone_number=user_data.phone_number or None,  # Handle empty string
            password=user_data.password,
            role=UserRole.GUEST,
            tenant_id=None,  # Mobile users don't belong to specific tenant
            status=UserStatus.ACTIVE,  # Mobile users are active immediately
            is_active=True  # Active for mobile users
        )
        
        user = crud.user.create(db, obj_in=user_create)
        
        logger.info(f"New user registered: {user.email} with role {user.role}")
        
        return schemas.UserRegistrationResponse(
            message="Registration successful. You can now log in.",
            user_id=user.id,
            status="active",
            email=user.email
        )
        
    except Exception as e:
        logger.error(f"Registration failed for {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )
