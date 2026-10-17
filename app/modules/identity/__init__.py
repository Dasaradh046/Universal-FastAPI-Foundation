"""Identity module.

Tenant, user, and role management.
"""
from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import router as api_router
from .models import RoleModel, Tenant, User
from .permissions import (
    ROLE_ASSIGN,
    ROLE_DELETE,
    ROLE_READ,
    ROLE_WRITE,
    TENANT_DELETE,
    TENANT_READ,
    TENANT_WRITE,
    USER_DELETE,
    USER_READ,
    USER_WRITE,
)
from .repositories import RoleRepository, TenantRepository, UserRepository
from .schemas import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    TenantCreate,
    TenantResponse,
    TenantStatusUpdate,
    TenantUpdate,
    UserCreate,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)
from .services import RoleService, TenantService, UserService

MANIFEST = ModuleManifest(
    id="identity",
    version="1.0.0",
    name="Identity Module",
    description="Tenant, user, and role management module",
    dependencies=[],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=api_router,
    models=[Tenant, User, RoleModel],
    permissions=[
        TENANT_READ,
        TENANT_WRITE,
        TENANT_DELETE,
        USER_READ,
        USER_WRITE,
        USER_DELETE,
        ROLE_READ,
        ROLE_WRITE,
        ROLE_DELETE,
        ROLE_ASSIGN,
    ],
)

__all__ = [
    "MANIFEST",
    "ROLE_ASSIGN",
    "ROLE_DELETE",
    "ROLE_READ",
    "ROLE_WRITE",
    "TENANT_DELETE",
    "TENANT_READ",
    "TENANT_WRITE",
    "USER_DELETE",
    "USER_READ",
    "USER_WRITE",
    "RoleCreate",
    "RoleModel",
    "RoleRepository",
    "RoleResponse",
    "RoleService",
    "RoleUpdate",
    "Tenant",
    "TenantCreate",
    "TenantRepository",
    "TenantResponse",
    "TenantService",
    "TenantStatusUpdate",
    "TenantUpdate",
    "User",
    "UserCreate",
    "UserRepository",
    "UserResponse",
    "UserService",
    "UserStatusUpdate",
    "UserUpdate",
    "api_router",
]
