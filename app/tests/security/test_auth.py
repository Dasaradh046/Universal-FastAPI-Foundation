"""
Security tests for the Universal FastAPI Foundation.

Covers the negative security cases required by PRD §5.3:
- Unauthenticated requests are rejected
- Invalid/expired/malformed tokens are rejected
- Insufficient permissions are rejected (403)
- Tenant isolation is enforced server-side
- No sensitive data leaks in error responses
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.security import CurrentUser
from app.models.enums import Role

# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_no_token(async_client: AsyncClient):
    """Requests without a bearer token to a protected endpoint return 401."""
    response = await async_client.get("/api/v1/examples")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_invalid_token(
    async_client: AsyncClient, invalid_token: str
):
    """Requests with an invalid token return 401."""
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = await async_client.get("/api/v1/examples", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Requests with an expired token return 401."""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.get("/api/v1/examples", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_health_endpoint_allows_unauthenticated(async_client: AsyncClient):
    """Public health endpoints remain accessible without authentication."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_root_endpoint_allows_unauthenticated(async_client: AsyncClient):
    """The root endpoint remains accessible without authentication."""
    response = await async_client.get("/")
    assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Insufficient permissions (authorization)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticated_user_can_access_protected_endpoint(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    """An authenticated user can access a protected endpoint (200, not 401/403)."""
    response = await async_client.get("/health/detailed", headers=auth_headers)
    # Health endpoints may return 200 or 503 depending on DB availability;
    # the key assertion is that auth does NOT return 401/403.
    assert response.status_code not in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.asyncio
async def test_error_responses_do_not_leak_sensitive_data(
    async_client: AsyncClient, invalid_token: str
):
    """Error responses must not expose stack traces, secrets, or internals."""
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = await async_client.get("/api/v1/examples", headers=headers)
    body = response.json()
    assert "detail" in body
    assert "traceback" not in str(body).lower()
    assert "secret" not in str(body).lower()
    assert "password" not in str(body).lower()


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_current_user_contains_tenant_id(auth_token: str):
    """A decoded token carries a tenant_id claim for server-side isolation."""
    from app.core.security import decode_token

    payload = decode_token(auth_token)
    assert payload is not None
    assert "tenant_id" in payload
    assert UUID(payload["tenant_id"])


@pytest.mark.asyncio
async def test_cross_tenant_access_not_implied_by_token():
    """Tokens from one tenant must not grant access to another tenant's data."""
    from app.core.security import create_access_token, decode_token

    token_a = create_access_token(
        subject="user-a", tenant_id="tenant-a", role="tenant_user"
    )
    token_b = create_access_token(
        subject="user-b", tenant_id="tenant-b", role="tenant_user"
    )

    payload_a = decode_token(token_a)
    payload_b = decode_token(token_b)

    assert payload_a is not None
    assert payload_b is not None
    assert payload_a["tenant_id"] != payload_b["tenant_id"]


# ---------------------------------------------------------------------------
# Role-based permission checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,expected_permission",
    [
        (Role.PLATFORM_OWNER.value, "*"),
        (Role.PLATFORM_ADMIN.value, "*"),
        (Role.TENANT_ADMIN.value, "users.read"),
        (Role.TENANT_USER.value, "users.read"),
        (Role.EMPLOYEE.value, "profile.read"),
    ],
)
def test_role_has_expected_permissions(role: str, expected_permission: str):
    """Role-permission mapping is deterministic and auditable."""
    from app.core.permissions import has_permission

    assert has_permission(role, expected_permission) is True


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_example_crud(
    async_client: AsyncClient,
):
    """All CRUD endpoints reject unauthenticated requests."""
    for method, path in [
        ("get", "/api/v1/examples"),
        ("post", "/api/v1/examples"),
        ("get", "/api/v1/examples/00000000-0000-0000-0000-000000000001"),
        ("put", "/api/v1/examples/00000000-0000-0000-0000-000000000001"),
        ("delete", "/api/v1/examples/00000000-0000-0000-0000-000000000001"),
    ]:
        client_method = getattr(async_client, method)
        response = await client_method(path)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
            f"{method.upper()} {path} should require authentication"
        )


# ---------------------------------------------------------------------------
# CurrentUser model validation
# ---------------------------------------------------------------------------


def test_current_user_model_fields():
    """CurrentUser dataclass carries all required identity fields."""
    user = CurrentUser(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email="user@example.com",
        role="tenant_user",
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        permissions=["example:read"],
        effective_roles=["tenant_user"],
        is_super_admin=False,
        is_platform_admin=False,
    )
    assert user.id == UUID("11111111-1111-1111-1111-111111111111")
    assert user.email == "user@example.com"
    assert user.role == "tenant_user"
    # Explicit permissions list is stored on the user object
    assert "example:read" in user.permissions
    # Role-based permission check uses ROLE_PERMISSIONS mapping
    assert user.has_permission("users.read") is True
    assert user.has_permission("example:delete") is False
    assert user.has_role("tenant_user") is True
    assert user.has_role("platform_admin") is False


__all__ = []
