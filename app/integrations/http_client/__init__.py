"""
Outbound HTTP client integration package.
"""

from app.integrations.http_client.client import HttpXClient
from app.integrations.http_client.contracts import (
    HTTPClientError,
    HTTPRequest,
    HTTPResponse,
)
from app.integrations.http_client.factory import get_http_client
from app.integrations.http_client.service import HTTPClientService

__all__ = [
    "get_http_client",
    "HTTPClientService",
    "HttpXClient",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPClientError",
]
