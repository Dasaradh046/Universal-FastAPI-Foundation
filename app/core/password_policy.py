"""
Password policy bridge — re-exports password-strength utilities from ``app.core.security``.

This module exists as a compatibility layer so modules can import
``from app.core.password_policy import ...`` without being tightly
coupled to the security sub-package's internal layout.
"""
from __future__ import annotations

from app.core.security import (
    check_password_strength,
    generate_temporary_password,
    PasswordStrength,
)

__all__ = [
    "check_password_strength",
    "generate_temporary_password",
    "PasswordStrength",
]
