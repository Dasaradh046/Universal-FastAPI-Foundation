"""
OpenTelemetry observability: metrics setup.

Configures OpenTelemetry metrics with OTLP exporter when enabled.
"""

from __future__ import annotations

from typing import Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_meter_provider_initialized = False


def setup_metrics(app=None) -> Optional[metrics.MeterProvider]:
    """Set up OpenTelemetry metrics.

    Args:
        app: Optional FastAPI app to instrument

    Returns:
        The MeterProvider if metrics is enabled, None otherwise
    """
    global _meter_provider_initialized

    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry metrics is disabled")
        return None

    if _meter_provider_initialized:
        logger.warning("OpenTelemetry metrics already initialized")
        return metrics.get_meter_provider()

    try:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError as e:
        logger.warning(
            f"OpenTelemetry exporter packages not installed: {e}. "
            "Install with: pip install opentelemetry-exporter-otlp "
            "opentelemetry-instrumentation-fastapi"
        )
        return None

    resource = Resource.create(
        {
            "service.name": settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    if otlp_endpoint:
        exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            headers=settings.OTEL_EXPORTER_OTLP_HEADERS or {},
        )
        reader = PeriodicExportingMetricReader(exporter)
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        logger.info(f"OpenTelemetry OTLP metrics exporter configured: {otlp_endpoint}")
    else:
        logger.warning(
            "OTEL_ENABLED=true but OTEL_EXPORTER_OTLP_ENDPOINT not set; "
            "no metrics will be exported"
        )
        provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(provider)
    _meter_provider_initialized = True

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app, meter_provider=provider
        )
        logger.info("FastAPI metrics instrumentation enabled")

    logger.info("OpenTelemetry metrics initialized")
    return provider


def shutdown_metrics():
    """Shut down OpenTelemetry metrics."""
    global _meter_provider_initialized

    if not _meter_provider_initialized:
        return

    provider = metrics.get_meter_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()

    _meter_provider_initialized = False
    logger.info("OpenTelemetry metrics shut down")


def get_meter(name: str) -> metrics.Meter:
    """Get a meter by name.

    Args:
        name: Meter name (typically __name__)

    Returns:
        An OpenTelemetry Meter instance
    """
    return metrics.get_meter(name)


__all__ = ["setup_metrics", "shutdown_metrics", "get_meter"]
