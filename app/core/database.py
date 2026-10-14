"""
Database configuration and session management.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Determine if we should use NullPool for testing
is_testing = "pytest" in sys.modules
poolclass = NullPool if is_testing else None

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    poolclass=poolclass,
)

# Create async session factory
session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession.

    Lifecycle:
    1. Open a session (checked out from the asyncpg pool).
    2. Yield the session to the route handler.
    3. On exception, roll back; otherwise commit.
    4. Close the session (returns the connection to the pool).
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield a plain async DB session without tenant context or auto-commit.

    Used by internal services that manage their own transaction boundaries.
    """
    async with session_factory() as session:
        yield session


async def create_db_and_tables() -> None:
    """Create database tables."""
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool.

    Call this on application shutdown and in test teardown.
    """
    await engine.dispose()


__all__ = [
    "engine",
    "session_factory",
    "get_db",
    "get_async_session",
    "create_db_and_tables",
    "dispose_engine",
]
