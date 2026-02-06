from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.tenant import Tenant

def auto_assign_tenant_admin(db: Session, user: User) -> bool:
    """
    Automatically assign tenant admin users to their tenant based on admin_email.
    Returns True if assignment was made, False otherwise.
    """
    # Only process admin users
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    if user.role not in admin_roles:
        return False
    
    # Skip if user already has a tenant assigned
    if user.tenant_id:
        return False
    
    # Find tenant where this user's email matches admin_email
    tenant = db.query(Tenant).filter(
        Tenant.admin_email == user.email,
        Tenant.is_active == True
    ).first()
    
    if tenant:
        print(f"AUTO-ASSIGN: Assigning user {user.email} to tenant {tenant.slug}")
        user.tenant_id = tenant.slug
        db.commit()
        return True
    
    return False
