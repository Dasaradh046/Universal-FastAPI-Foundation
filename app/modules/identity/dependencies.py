"""
Dependencies for the identity module.

Provides FastAPI dependency injection for repositories and services.
"""

from __future__ import annotations

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, get_audit_service
from app.core.database import get_db
from app.core.interfaces import IDatabaseService, DatabaseService
from app.modules.identity.repository import TenantRepository, UserRepository
from app.modules.identity.services import TenantService, UserService


def get_tenant_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantRepository:
    """Get tenant repository instance."""
    return TenantRepository(db)


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(db)


def get_tenant_service(
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(lambda: DatabaseService())],
) -> TenantService:
    """Get tenant service with all dependencies injected."""
    return TenantService(tenant_repo, audit_service, db_service)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(lambda: DatabaseService())],
) -> UserService:
    """Get user service with all dependencies injected."""
    return UserService(user_repo, tenant_repo, audit_service, db_service)


__all__ = [
    "get_tenant_repository",
    "get_user_repository",
    "get_tenant_service",
    "get_user_service",
]