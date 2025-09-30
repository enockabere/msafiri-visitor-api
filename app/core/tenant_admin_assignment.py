from sqlalchemy.orm import Session
from app.models.user import User
from app.models.tenant import Tenant

def assign_user_to_tenant_on_admin_change(db: Session, tenant: Tenant, old_admin_email: str = None) -> bool:
    """
    Automatically assign user to tenant when they become tenant admin.
    Returns True if assignment was made, False otherwise.
    """
    if not tenant.admin_email:
        return False
    
    # Find the user with the admin email
    user = db.query(User).filter(User.email == tenant.admin_email).first()
    if not user:
        print(f"TENANT-ADMIN: User {tenant.admin_email} not found")
        return False
    
    # Assign tenant to user if not already assigned
    if user.tenant_id != tenant.slug:
        print(f"TENANT-ADMIN: Assigning user {user.email} to tenant {tenant.slug}")
        user.tenant_id = tenant.slug
        db.commit()
        return True
    
    return False