"""
OpenTelemetry observability package.
"""

from app.core.observability.metrics import get_meter, setup_metrics, shutdown_metrics
from app.core.observability.prometheus import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    HTTP_RESPONSE_SIZE_BYTES,
    PrometheusMiddleware,
    metrics_endpoint,
)
from app.core.observability.tracing import get_tracer, setup_tracing, shutdown_tracing

__all__ = [
    "setup_tracing",
    "shutdown_tracing",
    "get_tracer",
    "setup_metrics",
    "shutdown_metrics",
    "get_meter",
    "PrometheusMiddleware",
    "metrics_endpoint",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_RESPONSE_SIZE_BYTES",
]
