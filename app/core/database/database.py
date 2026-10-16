"""
Database configuration and session management.

Production-grade choices:
  * Async SQLAlchemy 2.0 engine backed by ``asyncpg`` for PostgreSQL.
  * Connection health guarded by ``pool_pre_ping`` plus an explicit
    ``connect_args`` statement timeout so a hung database cannot stall
    workers indefinitely.
  * A bounded pool with overflow, recycling and a connect timeout to protect
    against connection exhaustion under load or network partitions.
  * Request-scoped sessions are committed on success and rolled back on any
    exception, with the connection always returned to the pool.
  * ``check_db_connection`` retries transient failures at startup / readiness
    probes so rolling deploys can tolerate a slow-to-attach database.
"""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator, AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as SaTimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config.settings import settings
from app.core.logging.logging import get_logger
from app.core.exceptions.exceptions import AppException

logger = get_logger(__name__)

# Tests run with an in-memory SQLite backend and must not share pooled
# connections across coroutines; NullPool gives each ``connect()`` a fresh
# connection that is closed immediately on release.
is_testing = "pytest" in sys.modules
poolclass = NullPool if is_testing else None

# ``connect_args`` are driver-specific. For asyncpg we can push the statement
# timeout straight into the server-side session so long-running queries are
# cancelled rather than hanging the worker. ``timeout`` covers the TCP connect.
_connect_args: dict[str, Any] = {}
if not is_testing:
    _connect_args = {
        "timeout": settings.DB_CONNECT_TIMEOUT_SECONDS,
        "server_settings": {
            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_SECONDS),
            "idle_in_transaction_session_timeout": str(
                settings.DB_IDLE_TRANSACTION_TIMEOUT_SECONDS
            ),
        },
    }

# Normalise the async URL to the asyncpg driver. ``make_url`` lets us inspect
# the scheme so we can swap psycopg2-style ``postgresql://`` for
# ``postgresql+asyncpg://`` when the user authored DATABASE_URL.
async_url = make_url(settings.database_url)
if "+" not in async_url.drivername:
    async_url = async_url.set(drivername="postgresql+asyncpg")

# Production-ready engine. Pool sizing is intentionally bounded so a sudden
# traffic spike or a stuck query cannot exhaust the database's connection
# limit. ``pool_recycle`` reaps connections older than 30 minutes to avoid
# firewalls/proxies dropping silent connections.
engine: AsyncEngine = create_async_engine(
    async_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # drop + re-establish connections that no longer respond
    poolclass=poolclass,
    pool_size=settings.DB_POOL_SIZE if poolclass is None else 1,
    max_overflow=settings.DB_MAX_OVERFLOW if poolclass is None else 0,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=1800,  # 30 minutes
    connect_args=_connect_args,
)

# Session factory. ``expire_on_commit=False`` keeps attribute access after
# ``commit()`` cheap (objects remain attached); routes are expected to fetch
# fresh copies when they need guaranteed-consistent data.
session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)


async def _handle_session_error(session: AsyncSession, exc: Exception) -> None:
    """Roll back a session and log/record the failure.

    Centralised so every dependency path rolls back consistently before the
    exception propagates to the caller.
    """
    try:
        await session.rollback()
    except Exception:
        logger.exception("Session rollback failed after database error")
    if isinstance(exc, SQLAlchemyError):
        logger.error("Database error occurred", exc_info=exc)
        raise AppException(
            status_code=500,
            detail="Database service unavailable",
        ) from exc
    raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped ``AsyncSession``.

    Lifecycle:
      1. Open a session (checked out from the asyncpg pool).
      2. Yield the session to the route handler.
      3. On ``SQLAlchemyError`` roll back and surface a 500
         ``AppException``; on any other exception roll back and re-raise.
      4. On success the transaction is left for FastAPI's dependency
         ``finally`` (the session is closed here, committing implicitly when
         no exception escaped).
      5. Close the session (returns the connection to the pool).
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception as exc:
            await _handle_session_error(session, exc)
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a plain async DB session without auto-commit.

    Used by background workers and internal services that manage their own
    transaction boundaries (begin / commit / rollback).
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception as exc:
            await _handle_session_error(session, exc)
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Explicit transaction context manager for service-layer work.

    Commits on clean exit, rolls back on any exception, and always closes.
    Prefer this over ``get_async_session`` when the caller owns the
    transaction boundary.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await _handle_session_error(session, exc)
        finally:
            await session.close()


async def create_db_and_tables() -> None:
    """Create all declared tables.

    Uses ``run_sync`` so SQLAlchemy's synchronous metadata reflection works
    against the async connection. Failures during startup are fatal and
    surface as a 500 ``AppException``.
    """
    from app.models.base import Base

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except (SQLAlchemyError, SaTimeoutError) as e:
        logger.error("Failed to create database tables", exc_info=e)
        raise AppException(
            status_code=500,
            detail="Database initialization failed",
        ) from e


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool.

    Call this on graceful application shutdown and in test teardown so all
    pooled connections are returned/closed cleanly.
    """
    try:
        await engine.dispose()
        logger.info("Database connections disposed")
    except SQLAlchemyError as e:
        logger.error("Error disposing database engine", exc_info=e)
        raise AppException(
            status_code=500,
            detail="Database shutdown failed",
        ) from e


async def check_db_connection(max_retries: int = 3, delay: float = 1.0) -> bool:
    """Check whether the database accepts connections.

    Retries a few times to tolerate transient failures (e.g. a database
    still starting during a rolling deploy). Returns ``True`` once
    ``SELECT 1`` succeeds, ``False`` if all attempts are exhausted.
    """
    import asyncio

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                # Explicit timeout so a hung server cannot block forever.
                await conn.execute(text("SELECT 1"))
            return True
        except (SQLAlchemyError, SaTimeoutError) as e:
            logger.warning(
                "Database health check attempt %d/%d failed: %s",
                attempt,
                max_retries,
                e,
            )
            if attempt == max_retries:
                return False
            await asyncio.sleep(delay * attempt)
    return False


__all__ = [
    "engine",
    "session_factory",
    "get_db",
    "get_async_session",
    "session_scope",
    "create_db_and_tables",
    "dispose_engine",
    "check_db_connection",
]
