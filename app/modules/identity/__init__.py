"Identity module."

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest, ModuleRouter

from .api.v1.routes import router as api_router
from .schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from .models import Tenant, User
from .services import TenantService, UserService
from .repository import TenantRepository, UserRepository
from .permissions import (
    TENANT_READ,
    TENANT_WRITE,
    TENANT_DELETE,
    USER_READ,
    USER_WRITE,
    USER_DELETE,
)

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="identity",
    version="1.0.0",
    name="Identity Module",
    description="Tenant and user management module",
    dependencies=[],  # Other module IDs this module depends on
    required_capabilities=[],  # Platform capabilities required
    optional_capabilities=["audit"],  # Optional capabilities
    router=api_router,
    models=[Tenant, User],
    permissions=[
        TENANT_READ,
        TENANT_WRITE,
        TENANT_DELETE,
        USER_READ,
        USER_WRITE,
        USER_DELETE,
    ],
    migrations_path="app.modules.identity.migrations",
)

# Export public interface
__all__ = [
    "api_router",
    "Tenant",
    "User",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "TenantService",
    "UserService",
    "TenantRepository",
    "UserRepository",
    "TENANT_READ",
    "TENANT_WRITE",
    "TENANT_DELETE",
    "USER_READ",
    "USER_WRITE",
    "USER_DELETE",
    "MANIFEST",
]
