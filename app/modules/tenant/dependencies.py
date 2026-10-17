"""
Dependencies for the tenant module.

Provides FastAPI dependency injection for repositories and services.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService
from app.core.audit import get_core_audit_service as get_audit_service
from app.core.database import get_db
from app.core.interfaces import DatabaseService, IDatabaseService
from app.modules.tenant.repositories import TenantContextRepository
from app.modules.tenant.services import TenantContextService


def get_tenant_context_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantContextRepository:
    """Get tenant context repository instance."""
    return TenantContextRepository(db)


def get_tenant_context_service(
    repository: Annotated[
        TenantContextRepository, Depends(get_tenant_context_repository)
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(lambda: DatabaseService())],
) -> TenantContextService:
    """Get tenant context service with all dependencies injected."""
    return TenantContextService(repository, audit_service, db_service)


__all__ = [
    "get_tenant_context_repository",
    "get_tenant_context_service",
]
