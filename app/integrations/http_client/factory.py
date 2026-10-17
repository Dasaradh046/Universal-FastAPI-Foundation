"""
Outbound HTTP client factory.
"""

from app.integrations.http_client.client import HttpXClient
from app.integrations.http_client.contracts import HTTPClient


def get_http_client() -> HTTPClient:
    """Factory function to get the configured HTTP client.

    Returns:
        An instance of the configured HTTP client
    """
    return HttpXClient()


__all__ = ["get_http_client"]
