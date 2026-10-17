"""
Tenant module — multi-tenancy context, resolution, and runtime management.

Provides tenant context resolution, tenant switching, tenant health/status,
and runtime tenant configuration. Complements the identity module's tenant
CRUD with runtime tenant-scoping concerns.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import tenant_router_v1
from .events import (
    TenantContextResolved,
    TenantSwitched,
)
from .permissions import (
    TENANT_CONTEXT_READ,
    TENANT_CONTEXT_WRITE,
    TENANT_SWITCH,
)
from .repositories import TenantContextRepository
from .schemas import TenantContext, TenantHealthResponse, TenantSwitchRequest
from .services import TenantContextService

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="tenant",
    version="1.0.0",
    name="Tenant Module",
    description=(
        "Multi-tenancy context resolution, tenant switching, "
        "and runtime management"
    ),
    dependencies=["identity"],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=tenant_router_v1,
    models=[],
    permissions=[
        TENANT_CONTEXT_READ,
        TENANT_CONTEXT_WRITE,
        TENANT_SWITCH,
    ],
)

__all__ = [
    "TenantContextService",
    "TenantContextRepository",
    "MANIFEST",
    "tenant_router_v1",
    "TenantContext",
    "TenantSwitchRequest",
    "TenantHealthResponse",
    "TENANT_CONTEXT_READ",
    "TENANT_CONTEXT_WRITE",
    "TENANT_SWITCH",
    "TenantContextResolved",
    "TenantSwitched",
]
