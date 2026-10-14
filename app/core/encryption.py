"""
Field-level encryption utilities using Fernet (AES-128-CBC + HMAC).

Used for encrypting sensitive data at rest in the database:
- TOTP secrets
- Recovery codes
- Any other PII that must not be stored in plaintext

The encryption key is provided via ``ENCRYPTION_KEY`` (a base64-encoded
Fernet key) or ``ENCRYPTION_KEY_FILE`` (path to a file containing the key).
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import TypeDecorator, Text

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_fernet() -> Any:
    """Get or create the Fernet cipher instance."""
    from cryptography.fernet import Fernet

    key = settings.ENCRYPTION_KEY
    if not key:
        if settings.ENCRYPTION_KEY_FILE:
            key_file = Path(settings.ENCRYPTION_KEY_FILE)
            if key_file.is_file():
                key = key_file.read_text().strip()
            else:
                raise RuntimeError(
                    f"Encryption key file not found: {key_file}"
                )
        else:
            raise RuntimeError(
                "ENCRYPTION_KEY or ENCRYPTION_KEY_FILE must be set for field encryption."
            )

    # Ensure the key is valid
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise RuntimeError(f"Invalid encryption key: {exc}") from exc


def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet."""
    if not value:
        return value
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_value(value: str) -> str:
    """Decrypt a Fernet-encrypted string value."""
    if not value:
        return value
    fernet = _get_fernet()
    decrypted = fernet.decrypt(value.encode("utf-8"))
    return decrypted.decode("utf-8")


class EncryptedText(TypeDecorator):
    """SQLAlchemy type for encrypted text fields.

    Values are encrypted on write and decrypted on read, transparently.
    The underlying column is a Text type in the database.

    Note: queries cannot filter on encrypted columns — the encryption is
    applied at the column type level, not at the query level.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        """Encrypt the value before writing to the database."""
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        """Decrypt the value after reading from the database."""
        if value is None:
            return None
        try:
            return decrypt_value(value)
        except Exception as exc:
            logger.warning("Failed to decrypt value: %s", exc)
            return None


__all__ = ["encrypt_value", "decrypt_value", "EncryptedText", "_get_fernet"]
