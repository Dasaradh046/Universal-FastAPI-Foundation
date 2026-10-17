"""
Dependencies for the auth module.

Provides FastAPI dependency injection for repositories and services.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.services import AuthService, get_auth_service


def get_auth_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> type:
    """Get auth repository class."""
    from app.modules.auth.repository import UserRepository

    return UserRepository


__all__ = ["get_auth_repository"]
