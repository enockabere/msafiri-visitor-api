from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.user_tenants import UserTenant, UserTenantRole
from app.models.user import User
from app.models.tenant import Tenant

class CRUDUserTenant(CRUDBase[UserTenant, dict, dict]):
    
    def assign_user_to_tenant(
        self,
        db: Session,
        *,
        user_id: int,
        tenant_id: str,
        role: UserTenantRole,
        assigned_by: str,
        is_primary: bool = False
    ) -> UserTenant:
        """Assign a user to a tenant with a specific role"""
        
        # Check if assignment already exists
        existing = db.query(UserTenant).filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id
        ).first()
        
        if existing:
            # Update existing assignment
            existing.role = role
            existing.is_active = True
            existing.assigned_by = assigned_by
            existing.assigned_at = func.now()
            if is_primary:
                existing.is_primary = True
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        
        # If setting as primary, remove primary flag from other tenants for this user
        if is_primary:
            db.query(UserTenant).filter(
                UserTenant.user_id == user_id,
                UserTenant.is_primary == True
            ).update({"is_primary": False})
        
        # Create new assignment
        user_tenant = UserTenant(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            assigned_by=assigned_by,
            is_primary=is_primary
        )
        
        db.add(user_tenant)
        db.commit()
        db.refresh(user_tenant)
        return user_tenant
    
    def get_user_tenants(self, db: Session, *, user_id: int) -> List[UserTenant]:
        """Get all tenants for a user"""
        return db.query(UserTenant).filter(
            UserTenant.user_id == user_id,
            UserTenant.is_active == True
        ).all()
    
    def get_tenant_users(self, db: Session, *, tenant_id: str) -> List[UserTenant]:
        """Get all users for a tenant"""
        return db.query(UserTenant).filter(
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True
        ).all()
    
    def get_user_primary_tenant(self, db: Session, *, user_id: int) -> Optional[UserTenant]:
        """Get user's primary tenant"""
        return db.query(UserTenant).filter(
            UserTenant.user_id == user_id,
            UserTenant.is_primary == True,
            UserTenant.is_active == True
        ).first()
    
    def remove_user_from_tenant(
        self,
        db: Session,
        *,
        user_id: int,
        tenant_id: str
    ) -> bool:
        """Remove user from tenant"""
        user_tenant = db.query(UserTenant).filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id
        ).first()
        
        if user_tenant:
            user_tenant.is_active = False
            user_tenant.deactivated_at = func.now()
            db.add(user_tenant)
            db.commit()
            return True
        return False
    
    def get_super_admins(self, db: Session) -> List[User]:
        """Get all super admins across all tenants"""
        return db.query(User).join(UserTenant).filter(
            UserTenant.role == UserTenantRole.SUPER_ADMIN,
            UserTenant.is_active == True,
            User.is_active == True
        ).distinct().all()

user_tenant = CRUDUserTenant(UserTenant)