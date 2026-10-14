"""
Dependencies for the example module.
"""
from __future__ import annotations

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.example_module.repository import ExampleRepository
from app.modules.example_module.service import ExampleService
from app.core.audit import AuditService
from app.core.interfaces import IDatabaseService, DatabaseService


def get_example_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ExampleRepository:
    """Get example repository."""
    return ExampleRepository(db)


def get_database_service() -> IDatabaseService:
    """Get database service implementation."""
    return DatabaseService()


def get_example_service(
    repository: Annotated[ExampleRepository, Depends(get_example_repository)],
    audit_service: Annotated[AuditService, Depends()],
    db_service: Annotated[IDatabaseService, Depends(get_database_service)],
) -> ExampleService:
    """Get example service."""
    return ExampleService(repository, audit_service, db_service)


# For backward compatibility, also provide a function that creates services with defaults
def get_example_service_simple(
    repository: Annotated[ExampleRepository, Depends(get_example_repository)]
) -> ExampleService:
    """Get example service with default dependencies."""
    audit_service = AuditService()
    db_service = DatabaseService()
    return ExampleService(repository, audit_service, db_service)


__all__ = [
    "get_example_repository", 
    "get_example_service",
    "get_example_service_simple"
]