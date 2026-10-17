"""
Identity repositories package.
"""
from __future__ import annotations

from app.modules.identity.repositories.role_repository import (
    RoleRepository,
    RoleRepositoryProtocol,
)
from app.modules.identity.repositories.tenant_repository import (
    TenantRepository,
    TenantRepositoryProtocol,
)
from app.modules.identity.repositories.user_repository import (
    UserRepository,
    UserRepositoryProtocol,
)

__all__ = [
    "RoleRepository",
    "RoleRepositoryProtocol",
    "TenantRepository",
    "TenantRepositoryProtocol",
    "UserRepository",
    "UserRepositoryProtocol",
]
