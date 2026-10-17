"""
Permissions for the auth module.
"""

from __future__ import annotations

from app.core.permissions import Permission

AUTH_LOGIN = Permission(
    code="auth:login",
    name="Login",
    description="Authenticate and obtain access tokens",
    module="auth",
    action=None,
)

AUTH_LOGOUT = Permission(
    code="auth:logout",
    name="Logout",
    description="Revoke current session",
    module="auth",
    action=None,
)

AUTH_REFRESH = Permission(
    code="auth:refresh",
    name="Refresh Token",
    description="Obtain new access token using refresh token",
    module="auth",
    action=None,
)

AUTH_PASSWORD_CHANGE = Permission(
    code="auth:password:change",
    name="Change Password",
    description="Change current user's password",
    module="auth",
    action=None,
)

AUTH_PASSWORD_RESET = Permission(
    code="auth:password:reset",
    name="Reset Password",
    description="Request and consume password reset tokens",
    module="auth",
    action=None,
)

AUTH_MFA = Permission(
    code="auth:mfa",
    name="Two-Factor Authentication",
    description="Manage and verify two-factor authentication",
    module="auth",
    action=None,
)

AUTH_SESSIONS = Permission(
    code="auth:sessions",
    name="Session Management",
    description="View and revoke device sessions",
    module="auth",
    action=None,
)

__all__ = [
    "AUTH_LOGIN",
    "AUTH_LOGOUT",
    "AUTH_REFRESH",
    "AUTH_PASSWORD_CHANGE",
    "AUTH_PASSWORD_RESET",
    "AUTH_MFA",
    "AUTH_SESSIONS",
]
