"""
Dependencies for the example module.

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
from app.modules.example_module.repositories import ExampleRepository
from app.modules.example_module.services import ExampleService


def get_example_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExampleRepository:
    """Get example repository instance."""
    return ExampleRepository(db)


def get_database_service() -> IDatabaseService:
    """Get database service implementation."""
    return DatabaseService()


def get_example_service(
    repository: Annotated[ExampleRepository, Depends(get_example_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    db_service: Annotated[IDatabaseService, Depends(get_database_service)],
) -> ExampleService:
    """Get example service with all dependencies injected."""
    return ExampleService(repository, audit_service, db_service)


__all__ = [
    "get_example_repository",
    "get_example_service",
]
