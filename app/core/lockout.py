"""
Lockout bridge — re-exports account-lockout utilities from ``app.core.security.lockout``.

This module exists as a compatibility layer so modules can import
``from app.core.lockout import ...`` without being tightly coupled
to the security sub-package's internal layout.
"""
from __future__ import annotations

from app.core.security.lockout import (
    check_login_lockout,
    record_failed_login,
    reset_login_failures,
    check_mfa_lockout,
    record_failed_mfa,
    reset_mfa_failures,
    LockoutState,
    unlock_account,
    unlock_mfa,
)

__all__ = [
    "check_login_lockout",
    "record_failed_login",
    "reset_login_failures",
    "check_mfa_lockout",
    "record_failed_mfa",
    "reset_mfa_failures",
    "LockoutState",
    "unlock_account",
    "unlock_mfa",
]
