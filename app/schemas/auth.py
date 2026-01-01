from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: Optional[int] = None
    role: Optional[str] = None
    all_roles: Optional[list] = None
    tenant_id: Optional[str] = None
    user_tenants: Optional[list] = None
    first_login: Optional[bool] = None
    must_change_password: Optional[bool] = None
    welcome_message: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    
class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    
class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_slug: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class ForcePasswordChangeRequest(BaseModel):
    new_password: str
    confirm_password: str

class UserRegistrationRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    tenant_slug: Optional[str] = None

class UserRegistrationResponse(BaseModel):
    message: str
    user_id: int
    status: str
    email: str

class FCMTokenUpdate(BaseModel):
    fcm_token: str