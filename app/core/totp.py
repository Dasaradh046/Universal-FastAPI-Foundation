"""
TOTP bridge — re-exports TOTP/recovery-code utilities from ``app.core.security``.

This module exists as a compatibility layer so modules can import
``from app.core.totp import ...`` without being tightly coupled
to the security sub-package's internal layout.
"""
from __future__ import annotations

from app.core.security import (
    generate_totp_secret,
    verify_totp,
    otpauth_uri,
    _render_qr_svg,
    generate_recovery_codes,
    hash_recovery_codes,
    redeem_recovery_code,
)

__all__ = [
    "generate_totp_secret",
    "verify_totp",
    "otpauth_uri",
    "_render_qr_svg",
    "generate_recovery_codes",
    "hash_recovery_codes",
    "redeem_recovery_code",
]
