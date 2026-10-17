"""
Outbound HTTP client service layer.
"""

from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.integrations.http_client.contracts import (
    HTTPRequest,
    HTTPResponse,
)
from app.integrations.http_client.factory import get_http_client

logger = get_logger(__name__)


class HTTPClientService:
    """Service for making outbound HTTP requests."""

    def __init__(self):
        self.client = get_http_client()

    async def request(self, request: HTTPRequest) -> HTTPResponse:
        """Make an HTTP request.

        Args:
            request: The HTTP request to make

        Returns:
            The HTTP response

        Raises:
            HTTPClientError: If the request fails
        """
        return await self.client.request(request)

    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        return await self.client.get(
            url, params=params, headers=headers, timeout=timeout
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
        return await self.client.post(
            url, json=json, data=data, params=params, headers=headers, timeout=timeout
        )

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.close()


__all__ = ["HTTPClientService"]
