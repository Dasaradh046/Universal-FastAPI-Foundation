"""
Audit module — security and compliance audit logging.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest
from app.modules.audit.api.v1.routes import router as audit_router_v1
from app.modules.audit.services import AuditServiceModule
from app.modules.audit.repository import AuditRepository
from app.modules.audit.permissions import (
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
    models=[],  # Uses AuditLog from app.models
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