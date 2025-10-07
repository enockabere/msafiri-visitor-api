import json
import logging
from typing import Optional, Dict, Any
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self):
        self.project_id = None
        self.credentials = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase credentials"""
        try:
            # Try to load Firebase service account key
            # This should be set as an environment variable or config file
            import os
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
            
            if service_account_path and os.path.exists(service_account_path):
                with open(service_account_path, 'r') as f:
                    service_account_info = json.load(f)
                
                self.credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/firebase.messaging']
                )
                self.project_id = service_account_info.get('project_id')
                logger.info("Firebase service initialized successfully")
            else:
                logger.warning("Firebase service account not found. Push notifications disabled.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase service: {str(e)}")
    
    def _get_access_token(self) -> Optional[str]:
        """Get Firebase access token"""
        try:
            if not self.credentials:
                return None
                
            self.credentials.refresh(Request())
            return self.credentials.token
        except Exception as e:
            logger.error(f"Failed to get Firebase access token: {str(e)}")
            return None
    
    def send_push_notification(
        self, 
        fcm_token: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send push notification to a specific device"""
        try:
            if not self.project_id or not self.credentials:
                logger.warning("Firebase not configured. Skipping push notification.")
                return False
            
            access_token = self._get_access_token()
            if not access_token:
                logger.error("Failed to get Firebase access token")
                return False
            
            url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            message = {
                "message": {
                    "token": fcm_token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "android": {
                        "notification": {
                            "click_action": "FLUTTER_NOTIFICATION_CLICK",
                            "sound": "default"
                        }
                    },
                    "apns": {
                        "payload": {
                            "aps": {
                                "sound": "default"
                            }
                        }
                    }
                }
            }
            
            if data:
                message["message"]["data"] = {k: str(v) for k, v in data.items()}
            
            response = requests.post(url, headers=headers, json=message)
            
            if response.status_code == 200:
                logger.info(f"Push notification sent successfully to token: {fcm_token[:20]}...")
                return True
            else:
                logger.error(f"Failed to send push notification. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return False
    
    def send_to_user(
        self, 
        db, 
        user_email: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send push notification to a user by email (looks up their FCM token)"""
        try:
            from app.models.user import User
            
            user = db.query(User).filter(User.email == user_email).first()
            if not user:
                logger.warning(f"User not found: {user_email}")
                return False
            
            # Check if user has FCM token stored
            fcm_token = getattr(user, 'fcm_token', None)
            if not fcm_token:
                logger.warning(f"No FCM token found for user: {user_email}")
                return False
            
            return self.send_push_notification(fcm_token, title, body, data)
            
        except Exception as e:
            logger.error(f"Error sending push notification to user {user_email}: {str(e)}")
            return False

# Global instance
firebase_service = FirebaseService()