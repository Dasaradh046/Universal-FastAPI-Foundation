"""
Auth module — authentication and session management.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest
from app.modules.auth.api.v1.routes import router as auth_router_v1
from app.modules.auth.services import AuthService, get_auth_service
from app.modules.auth.repository import UserRepository
from app.modules.auth.permissions import (
    AUTH_LOGIN,
    AUTH_LOGOUT,
    AUTH_REFRESH,
    AUTH_PASSWORD_CHANGE,
    AUTH_PASSWORD_RESET,
    AUTH_MFA,
    AUTH_SESSIONS,
)

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="auth",
    version="1.0.0",
    name="Authentication Module",
    description="User authentication, sessions, MFA, and password management",
    dependencies=["identity"],  # Depends on identity for tenant/user models
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=auth_router_v1,
    models=[],  # Uses models from identity/app.models
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
]