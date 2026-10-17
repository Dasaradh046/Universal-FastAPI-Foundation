"""
Shared test fixtures for the Universal FastAPI Foundation test suite.

Test environment overrides JWT to HS256 (no key files required) and points
database settings at a test database so security, contract, and integration
tests are runnable without external services.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Generator

import pytest  # noqa: E402

# ---- Test environment overrides (must be set before app imports) -----------
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-min-32-chars-long")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-chars-long!")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ubf_test"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/ubf_test"
)
os.environ.setdefault("OTEL_ENABLED", "False")
os.environ.setdefault("SENTRY_DSN", "")

# Re-instantiate settings with test overrides.
from app.core.config.settings import get_settings  # noqa: E402

get_settings.cache_clear()
settings = get_settings()  # noqa: F841

from fastapi.testclient import TestClient  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import session_factory  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# ASGI test client (httpx) — works with async routes
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Synchronous TestClient wrapper around the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client against the FastAPI app via ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ---------------------------------------------------------------------------
# Database session (uses the app's existing async engine)
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async SQLAlchemy session, rolled back after use."""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_token() -> str:
    """Create a valid JWT access token for a test user (HS256, no keys needed)."""
    return create_access_token(
        subject="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        role="tenant_user",
    )


@pytest.fixture
def admin_token() -> str:
    """Create a valid JWT access token for a platform admin."""
    return create_access_token(
        subject="33333333-3333-3333-3333-333333333333",
        tenant_id="22222222-2222-2222-2222-222222222222",
        role="platform_admin",
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Bearer authorization headers using a regular user token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """Bearer authorization headers using a platform admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def invalid_token() -> str:
    """An intentionally invalid JWT token."""
    return "invalid.token.string"


@pytest.fixture
def expired_token() -> str:
    """An expired JWT access token (negative lifetime)."""
    from datetime import timedelta

    from app.core.security.security import _create_token

    return _create_token(
        token_type="access",
        subject="expired-user",
        tenant_id="test-tenant-id",
        role="tenant_user",
        lifetime=timedelta(seconds=-1),
    )


__all__ = [
    "client",
    "async_client",
    "db_session",
    "auth_token",
    "admin_token",
    "auth_headers",
    "admin_headers",
    "invalid_token",
    "expired_token",
]
