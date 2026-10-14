"""
Dependencies for the identity module.
"""
from __future__ import annotations

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.repository import TenantRepository, UserRepository
from app.modules.identity.services import TenantService, UserService
from app.core.audit import AuditService
from app.core.interfaces import IDatabaseService, DatabaseService


def get_tenant_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantRepository:
    """Get tenant repository."""
    return TenantRepository(db)


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


def get_tenant_service(
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    audit_service: Annotated[AuditService, Depends()],
    db_service: Annotated[IDatabaseService, Depends(DatabaseService)],
) -> TenantService:
    """Get tenant service."""
    return TenantService(tenant_repo, audit_service, db_service)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)],
    audit_service: Annotated[AuditService, Depends()],
    db_service: Annotated[IDatabaseService, Depends(DatabaseService)],
) -> UserService:
    """Get user service."""
    return UserService(user_repo, tenant_repo, audit_service, db_service)


# For backward compatibility, also provide functions that create services with defaults
def get_tenant_service_simple(
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)]
) -> TenantService:
    """Get tenant service with default dependencies."""
    audit_service = AuditService()
    db_service = DatabaseService()
    return TenantService(tenant_repo, audit_service, db_service)


def get_user_service_simple(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    tenant_repo: Annotated[TenantRepository, Depends(get_tenant_repository)]
) -> UserService:
    """Get user service with default dependencies."""
    audit_service = AuditService()
    db_service = DatabaseService()
    return UserService(user_repo, tenant_repo, audit_service, db_service)
