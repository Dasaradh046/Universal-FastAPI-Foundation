"""
Password policy validation and generation.

This module provides password strength checking using the security module's
implementation, maintaining backward compatibility for imports that reference
``app.core.password_policy``.
"""

from __future__ import annotations

from app.core.security import PasswordStrength, check_password_strength, generate_temporary_password

__all__ = [
    "PasswordStrength",
    "check_password_strength",
    "generate_temporary_password",
]
