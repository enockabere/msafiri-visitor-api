from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.user import User, AuthProvider, UserRole, UserStatus
from app.schemas.user import UserCreate, UserUpdate, UserSSO
from app.core.security import get_password_hash, verify_password
import logging

logger = logging.getLogger(__name__)

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
    
    def get_by_reset_token(self, db: Session, *, token: str) -> Optional[User]:
        """Get user by password reset token"""
        return db.query(User).filter(User.password_reset_token == token).first()

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
            "role": obj_in.role or UserRole.GUEST,  # Default to GUEST if no role specified
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
        
        # Create corresponding UserRole entry for Guest users
        if db_obj.role == UserRole.GUEST:
            from app.models.user_roles import UserRole as UserRoleModel, RoleType
            guest_role = UserRoleModel(
                user_id=db_obj.id,
                role=RoleType.GUEST,
                granted_by="system",
                granted_at=func.now(),
                is_active=True
            )
            db.add(guest_role)
            db.commit()
        
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
   
    def authenticate_local(self, db: Session, *, email: str, password: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Traditional email/password authentication for LOCAL users and SSO users with passwords"""
        user = self.get_by_email(db, email=email, tenant_id=tenant_id)
        if not user:
            return None
        # Allow SSO users to login with password if they have one (for admin portal)
        # This enables dual authentication: SSO for mobile, password for admin portal
        if not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
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
        # First, try to find existing user by email (primary check)
        existing_user = self.get_by_email(db, email=user_data["email"])
        
        if existing_user:
            # Update existing user with latest SSO data
            update_data = {
                "full_name": user_data.get("full_name", existing_user.full_name),
                "department": user_data.get("department"),
                "job_title": user_data.get("job_title"),
                "external_id": user_data.get("external_id"),
                "azure_tenant_id": user_data.get("azure_tenant_id"),
                "last_login": func.now()
            }
            return self.update(db, db_obj=existing_user, obj_in=update_data)
        else:
            # Auto-register new user with role from invitation or default
            role = user_data.get("role", "guest")  # Use role from invitation if available
            return self.auto_register_sso_user(db, user_data=user_data, tenant_id=tenant_id, role=role)

    def auto_register_sso_user(self, db: Session, *, user_data: Dict[str, Any], tenant_id: Optional[str] = None, role: str = "guest") -> User:
        """
        Auto-register a new SSO user with minimal required data
        """
        # Convert string role to UserRole enum
        try:
            user_role = UserRole(role.upper())
        except ValueError:
            user_role = UserRole.GUEST
            
        # Create new user with minimal data from SSO
        new_user = User(
            email=user_data["email"],
            full_name=user_data.get("full_name", user_data["email"].split("@")[0]),  # Use email prefix if no name
            auth_provider=AuthProvider.MICROSOFT_SSO,
            external_id=user_data.get("external_id"),
            azure_tenant_id=user_data.get("azure_tenant_id"),
            department=user_data.get("department"),
            job_title=user_data.get("job_title"),
            tenant_id=tenant_id,
            role=user_role,  # Use role from invitation or default to GUEST
            status=UserStatus.ACTIVE,  # Active immediately for SSO users
            is_active=True,
            hashed_password=None,  # No password for SSO users
            auto_registered=True,  # Mark as auto-registered
            last_login=func.now()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Auto-registered new SSO user: {new_user.email} in tenant: {tenant_id}")
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

    def is_first_login(self, user: User) -> bool:
        """Check if this is the user's first login"""
        return user.last_login is None
    
    def record_login(self, db: Session, *, user: User) -> User:
        """Record user login and return updated user"""
        from datetime import datetime
        
        is_first = self.is_first_login(user)
        
        try:
            # Update last_login timestamp with Python datetime instead of SQL func
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Send first login welcome notification
            if is_first and user.tenant_id:
                from app.core.enhanced_notifications import notification_service
                try:
                    notification_service.notify_first_login_welcome(
                        db,
                        user=user,
                        tenant_id=user.tenant_id
                    )
                except Exception as e:
                    logger.error(f"Failed to send first login notification to {user.email}: {e}")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to record login for user {user.email}: {e}")
            db.rollback()
            # Return user without updating login time if database update fails
            return user
    
    def create_with_notifications(self, db: Session, *, obj_in: UserCreate, created_by: str) -> User:
        """Create user and trigger notifications"""
        user = self.create(db, obj_in=obj_in)
        
        # Send notifications
        if user.tenant_id:
            from app.core.enhanced_notifications import notification_service
            try:
                notification_service.notify_user_created(
                    db,
                    new_user=user,
                    created_by=created_by,
                    tenant_id=user.tenant_id,
                    is_first_login=True  # New users haven't logged in yet
                )
            except Exception as e:
                logger.error(f"Failed to send user creation notifications for {user.email}: {e}")
        
        return user
    
    def update_role_with_notifications(
        self, 
        db: Session, 
        *, 
        user: User, 
        new_role: UserRole, 
        changed_by: str
    ) -> User:
        """Update user role and send notifications"""
        old_role = user.role
        
        # Update the role
        updated_user = self.update(db, db_obj=user, obj_in={"role": new_role})
        
        # Send notifications if role actually changed
        if old_role != new_role and user.tenant_id:
            from app.core.enhanced_notifications import notification_service
            try:
                notification_service.notify_role_changed(
                    db,
                    user=updated_user,
                    old_role=old_role,
                    new_role=new_role,
                    changed_by=changed_by,
                    tenant_id=user.tenant_id
                )
            except Exception as e:
                logger.error(f"Failed to send role change notifications for {user.email}: {e}")
        
        return updated_user
    
    def update_status_with_notifications(
        self,
        db: Session,
        *,
        user: User,
        is_active: bool,
        status: UserStatus,
        changed_by: str
    ) -> User:
        """Update user status and send notifications"""
        old_status = user.status
        old_active = user.is_active
        
        # Update status
        updated_user = self.update(db, db_obj=user, obj_in={
            "is_active": is_active,
            "status": status
        })
        
        # Determine action for notifications
        if not old_active and is_active:
            action = "activated"
        elif old_active and not is_active:
            action = "deactivated"
        else:
            action = None
        
        # Send notifications if status actually changed
        if action and user.tenant_id:
            from app.core.enhanced_notifications import notification_service
            try:
                notification_service.notify_user_status_changed(
                    db,
                    user=updated_user,
                    action=action,
                    changed_by=changed_by,
                    tenant_id=user.tenant_id
                )
            except Exception as e:
                logger.error(f"Failed to send status change notifications for {user.email}: {e}")
        
        return updated_user
user = CRUDUser(User)
