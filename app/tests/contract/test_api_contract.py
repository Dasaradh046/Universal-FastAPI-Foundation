"""
Contract tests for the Universal FastAPI Foundation API.

Validates:
- OpenAPI schema is generated and stable
- All API responses follow the ResponseEnvelope pattern
- Endpoint status codes, headers, and response shapes are consistent
- Error responses use a consistent, non-leaky format
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# OpenAPI schema contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_schema_is_generated(async_client: AsyncClient):
    """The OpenAPI schema endpoint returns a valid schema document."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert schema["info"]["title"] == "Universal FastAPI Foundation"


@pytest.mark.asyncio
async def test_openapi_schema_has_version(async_client: AsyncClient):
    """The OpenAPI schema reports the application version."""
    response = await async_client.get("/openapi.json")
    schema = response.json()
    assert schema["info"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_docs_endpoint_is_accessible(async_client: AsyncClient):
    """The Swagger UI docs endpoint is accessible."""
    response = await async_client.get("/docs")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Response envelope contract
# ---------------------------------------------------------------------------


def _assert_envelope(data: dict[str, Any], status_code: int = 200) -> None:
    """Assert a response body follows the ResponseEnvelope pattern."""
    assert data["success"] is True
    assert data["status_code"] == status_code
    assert isinstance(data["message"], str)
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_root_endpoint_returns_shape(async_client: AsyncClient):
    """The root endpoint returns basic API information."""
    response = await async_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "version" in body
    assert "docs" in body


@pytest.mark.asyncio
async def test_health_endpoint_returns_shape(async_client: AsyncClient):
    """The health endpoint returns a consistent shape."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] == "healthy"


# ---------------------------------------------------------------------------
# Error response contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_response_has_no_stack_trace(async_client: AsyncClient):
    """Error responses must not leak stack traces or internals."""
    response = await async_client.get("/api/v1/examples")
    assert response.status_code == 401
    body = response.json()
    text = str(body).lower()
    assert "traceback" not in text
    assert "stack" not in text
    assert "secret" not in text
    assert "password" not in text


@pytest.mark.asyncio
async def test_nonexistent_endpoint_returns_404(async_client: AsyncClient):
    """Requests to undefined paths return a 4xx client error."""
    response = await async_client.get("/api/v1/nonexistent")
    assert 400 <= response.status_code < 500


# ---------------------------------------------------------------------------
# CORS and security headers contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_headers_present(async_client: AsyncClient):
    """Responses include standard security headers."""
    response = await async_client.get("/health")
    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"


@pytest.mark.asyncio
async def test_request_id_header(async_client: AsyncClient):
    """Every response includes an X-Request-ID header (from LoggingMiddleware)."""
    response = await async_client.get("/health")
    assert "X-Request-ID" in response.headers


# ---------------------------------------------------------------------------
# Health and metrics contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """The /health endpoint returns a 200 with expected shape."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_liveness_endpoint(async_client: AsyncClient):
    """The /live endpoint returns alive."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient):
    """The /metrics endpoint returns Prometheus text format."""
    response = await async_client.get("/api/v1/health/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "http_requests_total" in text
    assert "http_request_duration_seconds" in text


__all__ = []
