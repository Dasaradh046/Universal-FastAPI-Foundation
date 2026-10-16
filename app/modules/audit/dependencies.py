"""
Dependencies for the audit module.

Provides FastAPI dependency injection for repositories and services.
"""

from __future__ import annotations

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, get_core_audit_service
from app.core.database import get_db
from app.core.interfaces import IDatabaseService, DatabaseService
from app.modules.audit.repository import AuditRepository
from app.modules.audit.services import AuditServiceModule


def get_audit_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuditRepository:
    """Get audit repository instance."""
    return AuditRepository(db)


def get_audit_service(
    repository: Annotated[AuditRepository, Depends(get_audit_repository)],
    audit_service: Annotated[AuditService, Depends(get_core_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(lambda: DatabaseService())],
) -> AuditServiceModule:
    """Get audit service with all dependencies injected."""
    return AuditServiceModule(repository, audit_service, db_service)


__all__ = [
    "get_audit_repository",
    "get_audit_service",
]