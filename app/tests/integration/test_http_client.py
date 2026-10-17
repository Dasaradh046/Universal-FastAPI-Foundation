"""
Tests for the outbound HTTP client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.http_client.client import HttpXClient
from app.integrations.http_client.contracts import (
    HTTPClientError,
    HTTPRequest,
)


@pytest.fixture
def http_client():
    """Create an HttpXClient instance."""
    return HttpXClient(base_url="https://api.example.com", timeout=10.0, max_retries=2)


class TestHttpXClient:
    """Tests for the HttpXClient."""

    def test_client_initialization(self, http_client):
        """HttpXClient initializes with base URL, timeout, and retries."""
        assert http_client.base_url == "https://api.example.com"
        assert http_client.timeout == 10.0
        assert http_client.max_retries == 2

    def test_resolve_url_absolute(self, http_client):
        """Absolute URLs are returned unchanged."""
        assert (
            http_client._resolve_url("https://other.com/path")
            == "https://other.com/path"
        )

    def test_resolve_url_relative(self, http_client):
        """Relative URLs are resolved against base URL."""
        assert http_client._resolve_url("/path") == "https://api.example.com/path"

    def test_resolve_url_no_base(self):
        """URLs without a base are returned as-is."""
        client = HttpXClient()
        assert (
            client._resolve_url("https://api.example.com/path")
            == "https://api.example.com/path"
        )

    @pytest.mark.asyncio
    async def test_get_success(self, http_client):
        """A successful GET request returns an HTTPResponse."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"ok": true}'
        mock_response.url = "https://api.example.com/items"
        mock_response.is_closed = False

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch.object(http_client, "_get_client", return_value=mock_client):
            response = await http_client.get("/items")

        assert response.status_code == 200
        assert response.text == '{"ok": true}'
        assert response.url == "https://api.example.com/items"

    @pytest.mark.asyncio
    async def test_post_success(self, http_client):
        """A successful POST request returns an HTTPResponse."""
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = '{"id": 1}'
        mock_response.url = "https://api.example.com/items"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch.object(http_client, "_get_client", return_value=mock_client):
            response = await http_client.post("/items", json={"name": "test"})

        assert response.status_code == 201
        assert response.text == '{"id": 1}'

    @pytest.mark.asyncio
    async def test_http_status_error(self, http_client):
        """HTTP status errors raise HTTPClientError."""
        import httpx

        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not Found"
        mock_response.url = "https://api.example.com/missing"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.is_closed = False

        def raise_for_status():
            raise httpx.HTTPStatusError(
                "404", request=AsyncMock(), response=mock_response
            )

        mock_response.raise_for_status = raise_for_status
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch.object(http_client, "_get_client", return_value=mock_client):
            with pytest.raises(HTTPClientError) as exc_info:
                await http_client.get("/missing")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_connect_error_retries(self, http_client):
        """Connection errors are retried with backoff."""
        import httpx

        call_count = 0

        async def failing_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client.request = failing_request

        with patch.object(http_client, "_get_client", return_value=mock_client):
            with patch("asyncio.sleep", new=AsyncMock()):
                with pytest.raises(HTTPClientError):
                    await http_client.get("/items")

        assert call_count == 3  # max_retries (2) + 1 initial attempt

    @pytest.mark.asyncio
    async def test_close(self, http_client):
        """close() closes the underlying client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        http_client._client = mock_client

        await http_client.close()

        mock_client.aclose.assert_awaited_once()


class TestHTTPRequest:
    """Tests for the HTTPRequest contract."""

    def test_default_method_is_get(self):
        """HTTPRequest defaults to GET method."""
        req = HTTPRequest(url="https://example.com")
        assert req.method == "GET"

    def test_custom_method(self):
        """HTTPRequest supports custom methods."""
        req = HTTPRequest(method="PATCH", url="https://example.com/item/1")
        assert req.method == "PATCH"


class TestHTTPClientError:
    """Tests for the HTTPClientError contract."""

    def test_error_with_status_code(self):
        """HTTPClientError can carry a status code."""
        err = HTTPClientError("Not found", status_code=404)
        assert str(err) == "Not found"
        assert err.status_code == 404

    def test_error_with_provider_code(self):
        """HTTPClientError can carry a provider error code."""
        err = HTTPClientError("Failed", provider_error_code="connect_timeout")
        assert err.provider_error_code == "connect_timeout"
