"""
Auth module — authentication and session management.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import auth_router_v1
from .events import (
    MfaDisabled,
    MfaEnabled,
    PasswordChanged,
    PasswordResetCompleted,
    PasswordResetRequested,
    SessionRevoked,
    UserLoggedIn,
    UserLoggedOut,
)
from .permissions import (
    AUTH_LOGIN,
    AUTH_LOGOUT,
    AUTH_MFA,
    AUTH_PASSWORD_CHANGE,
    AUTH_PASSWORD_RESET,
    AUTH_REFRESH,
    AUTH_SESSIONS,
)
from .repository import UserRepository
from .services import AuthService, get_auth_service

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="auth",
    version="1.0.0",
    name="Authentication Module",
    description="User authentication, sessions, MFA, and password management",
    dependencies=["identity"],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=auth_router_v1,
    models=[],
    permissions=[
        AUTH_LOGIN,
        AUTH_LOGOUT,
        AUTH_REFRESH,
        AUTH_PASSWORD_CHANGE,
        AUTH_PASSWORD_RESET,
        AUTH_MFA,
        AUTH_SESSIONS,
    ],
)

__all__ = [
    "AuthService",
    "get_auth_service",
    "UserRepository",
    "MANIFEST",
    "auth_router_v1",
    "UserLoggedIn",
    "UserLoggedOut",
    "PasswordChanged",
    "PasswordResetRequested",
    "PasswordResetCompleted",
    "MfaEnabled",
    "MfaDisabled",
    "SessionRevoked",
]
