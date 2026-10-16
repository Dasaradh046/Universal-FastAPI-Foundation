"""
Encryption utilities for the Universal FastAPI Foundation.

Provides:
- Fernet-based field encryption for sensitive data (PII, tokens, secrets)
- Argon2 password hashing with secure defaults
- Key management from app/keys directory
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from argon2 import PasswordHasher
from sqlalchemy import Text, TypeDecorator

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption keys and operations."""
    
    _instance: Optional["EncryptionManager"] = None
    _fernet: Optional[Fernet] = None
    _private_key: Optional[bytes] = None
    _public_key: Optional[bytes] = None
    
    def __new__(cls) -> "EncryptionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._fernet is None:
            self._load_keys()
    
    def _load_keys(self) -> None:
        """Load encryption keys from the keys directory."""
        keys_dir = Path(__file__).parent.parent / "keys"
        
        # Load Fernet key
        fernet_path = keys_dir / "fernet" / "fernet_key.key"
        if fernet_path.exists():
            with open(fernet_path, "rb") as f:
                fernet_key = f.read().strip()
            self._fernet = Fernet(fernet_key)
            logger.info("Loaded Fernet key for field encryption")
        else:
            logger.warning("Fernet key not found at %s", fernet_path)
            # Generate a new one for development (not for production!)
            self._fernet = Fernet(Fernet.generate_key())
            logger.warning("Using generated Fernet key - NOT FOR PRODUCTION")
        
        # Load RSA keys for JWT
        private_key_path = keys_dir / "rsa" / "private_key.pem"
        public_key_path = keys_dir / "rsa" / "public_key.pem"
        
        if private_key_path.exists():
            with open(private_key_path, "rb") as f:
                self._private_key = f.read()
            logger.info("Loaded RSA private key for JWT signing")
        else:
            logger.warning("RSA private key not found at %s", private_key_path)
        
        if public_key_path.exists():
            with open(public_key_path, "rb") as f:
                self._public_key = f.read()
            logger.info("Loaded RSA public key for JWT verification")
        else:
            logger.warning("RSA public key not found at %s", public_key_path)
    
    @property
    def fernet(self) -> Fernet:
        "Get the Fernet instance for field extraction."
        if self._fernet is None:
            self._load_keys()
        assert self._fernet is not None, 'Fernet key should be initialized by _load_keys'
        return self._fernet

    @property
    def private_key(self) -> Optional[bytes]:
        """Get the RSA private key."""
        return self._private_key
    
    @property
    def public_key(self) -> Optional[bytes]:
        """Get the RSA public key."""
        return self._public_key


# Singleton instance
encryption_manager = EncryptionManager()


def encrypt_field(value: str) -> str:
    """
    Encrypt a string field using Fernet.
    
    Args:
        value: The plaintext value to encrypt.
        
    Returns:
        Base64-encoded encrypted value.
    """
    if not value:
        return value
    encrypted = encryption_manager.fernet.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_field(encrypted_value: str) -> str:
    """
    Decrypt a Fernet-encrypted field.
    
    Args:
        encrypted_value: The base64-encoded encrypted value.
        
    Returns:
        The decrypted plaintext value.
        
    Raises:
        InvalidToken: If the token is invalid or corrupted.
    """
    if not encrypted_value:
        return encrypted_value
    try:
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = encryption_manager.fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except InvalidToken:
        logger.error("Failed to decrypt field - invalid token")
        raise
    except Exception as e:
        logger.error("Failed to decrypt field: %s", e)
        raise


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Uses secure defaults from config:
    - Memory cost: 64 MB (65536 KB)
    - Time cost: 3 iterations
    - Parallelism: 4 threads
    - Hash length: 32 bytes
    - Salt length: 16 bytes
    
    Args:
        password: The plaintext password to hash.
        
    Returns:
        Argon2 hashed password string.
    """
    from app.core.config import settings
    ph = PasswordHasher(
        time_cost=settings.ARGON2_TIME_COST,
        memory_cost=settings.ARGON2_MEMORY_COST,
        parallelism=settings.ARGON2_PARALLELISM,
        hash_len=settings.ARGON2_HASH_LEN,
        salt_len=settings.ARGON2_SALT_LEN,
    )
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against an Argon2 hash.
    
    Args:
        password: The plaintext password to verify.
        hashed: The Argon2 hash to verify against.
        
    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return PasswordHasher().verify(hashed, password)
    except Exception as e:
        logger.error("Password verification error: %s", e)
        return False


def needs_rehash(hashed: str) -> bool:
    """
    Check if a password hash needs to be rehashed with current parameters.
    
    Args:
        hashed: The existing Argon2 hash.
        
    Returns:
        True if rehash is needed, False otherwise.
    """
    try:
        return PasswordHasher().check_needs_rehash(hashed)
    except Exception:
        return True


class EncryptedField(TypeDecorator):
    """SQLAlchemy type decorator for automatically encrypting/decrypting fields."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt value when loading from database."""
        if value is None:
            return None
        return decrypt_field(value)


EncryptedText = EncryptedField(Text)


def get_private_key_pem() -> Optional[bytes]:
    """Get the RSA private key in PEM format."""
    return encryption_manager.private_key


def get_public_key_pem() -> Optional[bytes]:
    """Get the RSA public key in PEM format."""
    return encryption_manager.public_key


__all__ = [
    "encryption_manager",
    "encrypt_field",
    "decrypt_field",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "EncryptedField",
    "get_private_key_pem",
    "get_public_key_pem",
]


