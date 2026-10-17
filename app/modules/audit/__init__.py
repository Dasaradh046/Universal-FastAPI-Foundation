"""
Audit module — security and compliance audit logging.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest
from .router import router as audit_router_v1
from .services import AuditServiceModule
from .repository import AuditRepository
from .permissions import (
    AUDIT_READ,
    AUDIT_EXPORT,
)

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="audit",
    version="1.0.0",
    name="Audit Module",
    description="Security and compliance audit logging",
    dependencies=["auth", "identity"],
    required_capabilities=[],
    optional_capabilities=[],
    router=audit_router_v1,
    models=[],
    permissions=[
        AUDIT_READ,
        AUDIT_EXPORT,
    ],
)

__all__ = [
    "AuditServiceModule",
    "AuditRepository",
    "MANIFEST",
    "audit_router_v1",
]
