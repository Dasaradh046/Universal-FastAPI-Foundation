"""
Outbound HTTP client contracts.

Defines the interface for making outbound HTTP requests to external services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel, Field


class HTTPRequest(BaseModel):
    """An outbound HTTP request."""

    method: str = "GET"
    url: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    json: Optional[Any] = None
    data: Optional[Any] = None
    timeout: Optional[float] = None


class HTTPResponse(BaseModel):
    """An outbound HTTP response."""

    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    text: Optional[str] = None
    url: str


class HTTPClient(Protocol):
    """Protocol defining the outbound HTTP client interface."""

    async def request(self, request: HTTPRequest) -> HTTPResponse:
        """Make an HTTP request.

        Args:
            request: The HTTP request to make

        Returns:
            The HTTP response

        Raises:
            HTTPClientError: If the request fails
        """
        ...

    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        ...

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
        ...

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
        ...

    async def delete(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """Make a DELETE request."""
        ...


class HTTPClientError(Exception):
    """Exception raised when an HTTP client request fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        provider_error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.provider_error_code = provider_error_code


class HTTPClientBaseService(ABC):
    """Abstract base class for HTTP client services."""

    @abstractmethod
    async def request(self, request: HTTPRequest) -> HTTPResponse:
        pass

    @abstractmethod
    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        pass

    @abstractmethod
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
        pass
