"""Encryption utility for sensitive data."""
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import os


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        key = settings.ENCRYPTION_KEY if hasattr(settings, 'ENCRYPTION_KEY') else self._generate_key()
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    @staticmethod
    def _generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        if not data:
            return ""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string."""
        if not encrypted_data:
            return ""
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(decoded)
        return decrypted.decode()


# Global encryption service instance
encryption_service = EncryptionService()
