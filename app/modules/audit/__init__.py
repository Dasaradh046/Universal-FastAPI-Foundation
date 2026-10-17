"""
Audit module — security and compliance audit logging.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import audit_router_v1
from .events import (
    AuditLogCreated,
    AuditLogsExported,
)
from .permissions import (
    AUDIT_EXPORT,
    AUDIT_READ,
)
from .repositories import AuditRepository, AuditRepositoryProtocol
from .services import AuditServiceModule

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
    "AuditRepositoryProtocol",
    "MANIFEST",
    "audit_router_v1",
    "AUDIT_READ",
    "AUDIT_EXPORT",
    "AuditLogCreated",
    "AuditLogsExported",
]
