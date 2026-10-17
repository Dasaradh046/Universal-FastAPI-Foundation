"""
Outbound HTTP client implementation using httpx.

Provides a reusable async HTTP client with retry logic, timeout
configuration, and request/response logging.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.http_client.contracts import (
    HTTPClient,
    HTTPClientError,
    HTTPRequest,
    HTTPResponse,
)

logger = get_logger(__name__)


class HttpXClient(HTTPClient):
    """httpx-based HTTP client implementation."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url or settings.HTTP_CLIENT_BASE_URL
        self.timeout = timeout or float(settings.HTTP_CLIENT_TIMEOUT)
        self.max_retries = (
            max_retries if max_retries is not None else settings.HTTP_CLIENT_MAX_RETRIES
        )
        self.default_headers = default_headers or settings.HTTP_CLIENT_DEFAULT_HEADERS

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the underlying httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=self.default_headers,
            )
        return self._client

    async def close(self):
        """Close the underlying httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _resolve_url(self, url: str) -> str:
        """Resolve a URL against the base URL if it's relative."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        return url

    async def _retry_request(self, func, *args, **kwargs):
        """Execute a request with exponential backoff retries."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = min(2**attempt, 10)
                    logger.warning(
                        "HTTP request attempt"
                        f" {attempt + 1} failed, retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)
        raise last_error

    async def request(self, request: HTTPRequest) -> HTTPResponse:
        """Make an HTTP request.

        Args:
            request: The HTTP request to make

        Returns:
            The HTTP response

        Raises:
            HTTPClientError: If the request fails
        """
        url = self._resolve_url(request.url)
        timeout = httpx.Timeout(request.timeout or self.timeout)
        headers = {**self.default_headers, **(request.headers or {})}

        client = await self._get_client()

        async def _do_request():
            start = time.time()
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.params,
                json=request.json,
                data=request.data,
                timeout=timeout,
            )
            response.raise_for_status()
            duration_ms = (time.time() - start) * 1000
            logger.info(
                f"HTTP {request.method} {url} ->"
                f" {response.status_code} ({duration_ms:.1f}ms)"
            )
            return response

        try:
            response = await self._retry_request(_do_request)
        except httpx.HTTPStatusError as e:
            raise HTTPClientError(
                f"HTTP request failed: {e.response.status_code} {e.response.text}",
                status_code=e.response.status_code,
                provider_error_code=str(e.response.status_code),
            ) from e
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise HTTPClientError(
                f"HTTP request failed: {str(e)}",
                provider_error_code=type(e).__name__,
            ) from e
        except Exception as e:
            raise HTTPClientError(
                f"HTTP request failed: {str(e)}",
                provider_error_code=type(e).__name__,
            ) from e

        return HTTPResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            text=response.text,
            url=str(response.url),
        )

    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        return await self.request(
            HTTPRequest(
                method="GET", url=url, params=params, headers=headers, timeout=timeout
            )
        )

    async def post(
        self,
        url: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a POST request."""
        return await self.request(
            HTTPRequest(
                method="POST",
                url=url,
                json=json,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        )

    async def put(
        self,
        url: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a PUT request."""
        return await self.request(
            HTTPRequest(
                method="PUT",
                url=url,
                json=json,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        )

    async def delete(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a DELETE request."""
        return await self.request(
            HTTPRequest(
                method="DELETE",
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        )


__all__ = ["HttpXClient"]
