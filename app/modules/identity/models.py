"""
SQLAlchemy models for the identity module.

These models are re-exported from app.models for centralized model management.
See app/models/user.py, app/models/tenant.py for the full implementations.
"""
from __future__ import annotations

from app.models.tenant import Tenant
from app.models.user import (
    Permission,
    RoleModel,
    RolePermission,
    User,
    UserRole,
    UserSession,
)

__all__ = [
    "Permission",
    "RoleModel",
    "RolePermission",
    "Tenant",
    "User",
    "UserRole",
    "UserSession",
]
