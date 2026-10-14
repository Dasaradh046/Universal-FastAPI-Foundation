"""
TOTP (Time-based One-Time Password) utilities.

This module provides 2FA/TFA utilities for authentication, maintaining
backward compatibility for imports that reference ``app.core.totp``.
"""

from __future__ import annotations

from app.core.security import (
    generate_totp_secret,
    verify_totp,
    otpauth_uri,
    generate_recovery_codes,
    hash_recovery_codes,
    redeem_recovery_code,
)

__all__ = [
    "generate_totp_secret",
    "verify_totp",
    "otpauth_uri",
    "generate_recovery_codes",
    "hash_recovery_codes",
    "redeem_recovery_code",
]
