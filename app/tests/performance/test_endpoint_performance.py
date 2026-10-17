"""
Performance tests using pytest.

These tests verify response times for key API endpoints under
light load. They are not a replacement for dedicated load testing
with Locust or k6.
"""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_response_time(async_client: AsyncClient):
    """Health endpoint should respond quickly."""
    start = time.perf_counter()
    response = await async_client.get("/health")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.0, f"Health endpoint took {elapsed:.3f}s (expected < 1.0s)"


@pytest.mark.asyncio
async def test_root_endpoint_response_time(async_client: AsyncClient):
    """Root endpoint should respond quickly."""
    start = time.perf_counter()
    response = await async_client.get("/")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 1.0, f"Root endpoint took {elapsed:.3f}s (expected < 1.0s)"
