from typing import Optional, Dict, Any, List
import requests
from fastapi import HTTPException, status
from app.core.config import settings

class MicrosoftSSO:
    """Handle Microsoft SSO authentication with auto-registration"""
    
    def __init__(self):
        self.tenant_id = settings.AZURE_TENANT_ID
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
    
    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """Verify Microsoft access token and get user info"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{self.graph_endpoint}/me", headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Microsoft access token"
                )
            
            user_data = response.json()
            
            # Get additional user details
            profile_response = requests.get(
                f"{self.graph_endpoint}/me?$select=id,displayName,mail,userPrincipalName,department,jobTitle,officeLocation",
                headers=headers
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                user_data.update(profile_data)
            
            return {
                "external_id": user_data.get("id"),
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "full_name": user_data.get("displayName"),
                "department": user_data.get("department"),
                "job_title": user_data.get("jobTitle"),
                "azure_tenant_id": self.tenant_id
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to verify Microsoft token: {str(e)}"
            )
    
    def get_tenant_from_email(self, email: str) -> Optional[str]:
        """Map email domain to application tenant"""
        domain_to_tenant = {
            "msf-kenya.org": "msf-kenya",
            "msf-uganda.org": "msf-uganda",
            "msf-somalia.org": "msf-somalia",
            "msf.org": "msf-global",  # Global MSF
            # Add more mappings
        }
        
        if "@" in email:
            domain = email.split("@")[1].lower()
            return domain_to_tenant.get(domain)
        return None
    
    def is_msf_email(self, email: str) -> bool:
        """Check if email belongs to MSF organization"""
        msf_domains = [
            "msf.org",
            "msf-kenya.org", 
            "msf-uganda.org",
            "msf-somalia.org",
            "doctorswithoutborders.org",
            "msf.ch",  # MSF Switzerland
            "msf.fr",  # MSF France
            "msf.be",  # MSF Belgium
            # Add all MSF domains
        ]
        
        if "@" in email:
            domain = email.split("@")[1].lower()
            return domain in msf_domains
        return False
    
    def determine_auto_role(self, user_data: Dict[str, Any]) -> str:
        """
        Determine what role to assign to auto-registered users
        based on their profile information
        """
        email = user_data.get("email", "").lower()
        job_title = user_data.get("job_title", "").lower()
        department = user_data.get("department", "").lower()
        
        # MSF staff get STAFF role, others get GUEST
        if self.is_msf_email(email):
            # You can add more sophisticated role detection here
            if any(keyword in job_title for keyword in ["director", "coordinator", "manager"]):
                return "staff"  # Higher level staff
            elif any(keyword in department for keyword in ["medical", "logistic", "finance", "hr"]):
                return "staff"  # Department staff
            else:
                return "staff"  # Default for MSF staff
        else:
            return "guest"  # External users
