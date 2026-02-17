"""Encryption utility for sensitive data."""
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
            # Convert hex key to Fernet-compatible base64 key
            key_bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
            # Fernet requires exactly 32 bytes, use first 32 bytes
            key_bytes = key_bytes[:32]
            # Encode as URL-safe base64
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self.cipher = Fernet(fernet_key)
        else:
            # Generate new key if not provided
            self.cipher = Fernet(Fernet.generate_key())
    
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
