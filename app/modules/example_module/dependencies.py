"""
Dependencies for the example module.
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.example_module.repository import ExampleRepository
from app.modules.example_module.service import ExampleService


def get_example_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ExampleRepository:
    """Get example repository."""
    return ExampleRepository(db)


def get_example_service(
    repository: Annotated[ExampleRepository, Depends(get_example_repository)]
) -> ExampleService:
    """Get example service."""
    return ExampleService(repository)
