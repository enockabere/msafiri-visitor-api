from typing import List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_roles import UserRole, RoleType

def has_any_role(user: User, db: Session, required_roles: List[str]) -> bool:
    """Check if user has any of the required roles"""
    # Check primary role first (for backward compatibility)
    if user.role and user.role.value in required_roles:
        return True
    
    # Check additional roles from user_roles table
    user_roles = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.is_active == True
    ).all()
    
    user_role_names = [role.role.value for role in user_roles]
    return any(role in required_roles for role in user_role_names)

def has_transport_permissions(user: User, db: Session) -> bool:
    """Check if user has permissions for transport management"""
    required_roles = ["super_admin", "mt_admin", "hr_admin", "SUPER_ADMIN", "MT_ADMIN", "HR_ADMIN"]
    return has_any_role(user, db, required_roles)

def has_accommodation_permissions(user: User, db: Session) -> bool:
    """Check if user has permissions for accommodation management"""
    required_roles = ["super_admin", "mt_admin", "hr_admin", "SUPER_ADMIN", "MT_ADMIN", "HR_ADMIN"]
    return has_any_role(user, db, required_roles)