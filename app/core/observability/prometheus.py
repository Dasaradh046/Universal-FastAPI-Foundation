"""
Prometheus metrics exposition.

Defines HTTP request counters, duration histograms, and status code
breakdowns, plus a middleware that records metrics for every request.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

HTTP_RESPONSE_SIZE_BYTES = Counter(
    "http_response_size_bytes",
    "Total size of HTTP responses in bytes",
    ["method", "endpoint"],
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class PrometheusMiddleware:
    """ASGI middleware that records Prometheus metrics for each request."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        method = request.method
        path = request.url.path

        # Normalize the endpoint label to avoid high-cardinality paths
        endpoint = self._normalize_endpoint(path)

        start = time.time()

        async def _send(message):
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 0))
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status_code=status_code
                ).inc()
            await send(message)

        await self.app(scope, receive, _send)

        duration = time.time() - start
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """Normalize a URL path to a low-cardinality endpoint label.

        Replaces numeric path segments with ``{id}`` so that e.g.
        ``/api/v1/users/123`` and ``/api/v1/users/456`` share a label.
        """
        segments = [s for s in path.split("/") if s]
        normalized = []
        for seg in segments:
            if seg.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(seg)
        return "/" + "/".join(normalized) if normalized else "/"


async def metrics_endpoint() -> Response:
    """Return the latest Prometheus metrics in text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


__all__ = [
    "PrometheusMiddleware",
    "metrics_endpoint",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_RESPONSE_SIZE_BYTES",
]
