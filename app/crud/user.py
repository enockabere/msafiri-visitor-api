from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.user import User, AuthProvider, UserRole, UserStatus
from app.schemas.user import UserCreate, UserUpdate, UserSSO
from app.core.security import get_password_hash, verify_password

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    
    def get_by_email(self, db: Session, *, email: str, tenant_id: Optional[str] = None) -> Optional[User]:
        query = db.query(User).filter(User.email == email)
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
        return query.first()
    
    def get_by_external_id(self, db: Session, *, external_id: str, auth_provider: AuthProvider) -> Optional[User]:
        return db.query(User).filter(
            User.external_id == external_id,
            User.auth_provider == auth_provider
        ).first()

    def get_by_tenant(self, db: Session, *, tenant_id: str, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            db.query(User)
            .filter(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        # Handle both local and SSO user creation
        create_data = {
            "email": obj_in.email,
            "full_name": obj_in.full_name,
            "phone_number": obj_in.phone_number,
            "role": obj_in.role,
            "tenant_id": obj_in.tenant_id,
            "auth_provider": obj_in.auth_provider,
            "external_id": obj_in.external_id,
            "azure_tenant_id": obj_in.azure_tenant_id,
            "department": obj_in.department,
            "job_title": obj_in.job_title
        }
        
        # Only hash password for local auth users
        if obj_in.auth_provider == AuthProvider.LOCAL and obj_in.password:
            create_data["hashed_password"] = get_password_hash(obj_in.password)
        else:
            create_data["hashed_password"] = None
        
        db_obj = User(**create_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    # ========== MISSING METHODS (THIS IS WHAT YOU NEED) ==========
    
    def authenticate_local(self, db: Session, *, email: str, password: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Traditional email/password authentication for LOCAL users"""
        user = self.get_by_email(db, email=email, tenant_id=tenant_id)
        if not user:
            return None
        if user.auth_provider != AuthProvider.LOCAL:
            return None
        if not user.hashed_password or not verify_password(password, user.hashed_password):
            return None
        return user

    def authenticate(self, db: Session, *, email: str, password: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Legacy method - calls authenticate_local"""
        return self.authenticate_local(db, email=email, password=password, tenant_id=tenant_id)

    def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active

    def create_or_update_sso_user(self, db: Session, *, user_data: Dict[str, Any], tenant_id: Optional[str] = None) -> User:
        """
        Create or update user from SSO data - supports auto-registration
        """
        # First, try to find existing user by external_id
        existing_user = self.get_by_external_id(
            db, 
            external_id=user_data["external_id"], 
            auth_provider=AuthProvider.MICROSOFT_SSO
        )
        
        if existing_user:
            # Update existing user with latest SSO data
            update_data = {
                "full_name": user_data["full_name"],
                "department": user_data.get("department"),
                "job_title": user_data.get("job_title"),
                "profile_picture_url": user_data.get("profile_picture_url"),
                "last_login": func.now()
            }
            return self.update(db, db_obj=existing_user, obj_in=update_data)
        else:
            # Try to find by email (in case external_id changed)
            existing_user_by_email = self.get_by_email(db, email=user_data["email"])
            if existing_user_by_email and existing_user_by_email.auth_provider == AuthProvider.MICROSOFT_SSO:
                # Update the external_id and other fields
                update_data = {
                    "external_id": user_data["external_id"],
                    "full_name": user_data["full_name"],
                    "department": user_data.get("department"),
                    "job_title": user_data.get("job_title"),
                    "profile_picture_url": user_data.get("profile_picture_url"),
                    "last_login": func.now()
                }
                return self.update(db, db_obj=existing_user_by_email, obj_in=update_data)
            else:
                # Auto-register new user
                return self.auto_register_sso_user(db, user_data=user_data, tenant_id=tenant_id)

    def auto_register_sso_user(self, db: Session, *, user_data: Dict[str, Any], tenant_id: Optional[str] = None) -> User:
        """
        Auto-register a new SSO user (no pre-invitation required)
        """
        from app.core.sso import MicrosoftSSO
        
        ms_sso = MicrosoftSSO()
        
        # Determine role based on user profile
        auto_role = ms_sso.determine_auto_role(user_data)
        
        # Create new user with auto-registration
        new_user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            auth_provider=AuthProvider.MICROSOFT_SSO,
            external_id=user_data["external_id"],
            azure_tenant_id=user_data.get("azure_tenant_id"),
            department=user_data.get("department"),
            job_title=user_data.get("job_title"),
            profile_picture_url=user_data.get("profile_picture_url"),
            tenant_id=tenant_id,
            role=UserRole(auto_role),
            status=UserStatus.ACTIVE,  # Active immediately for MSF staff
            is_active=True,
            hashed_password=None,
            auto_registered=True,  # Mark as auto-registered
            last_login=func.now()
        )
        
        # If it's not MSF staff, require approval
        if auto_role == "guest":
            new_user.status = UserStatus.PENDING_APPROVAL
            new_user.is_active = False  # Inactive until approved
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def get_pending_approvals(self, db: Session, *, tenant_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users pending approval"""
        query = db.query(User).filter(User.status == UserStatus.PENDING_APPROVAL)
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        return query.offset(skip).limit(limit).all()
    
    def approve_user(self, db: Session, *, user_id: int, approved_by: str) -> User:
        """Approve a pending user"""
        user = self.get(db, id=user_id)
        if not user:
            raise ValueError("User not found")
        
        update_data = {
            "status": UserStatus.ACTIVE,
            "is_active": True,
            "approved_by": approved_by,
            "approved_at": func.now()
        }
        return self.update(db, db_obj=user, obj_in=update_data)

user = CRUDUser(User)