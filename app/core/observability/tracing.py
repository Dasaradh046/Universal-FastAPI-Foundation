"""
OpenTelemetry observability: tracing setup.

Configures OpenTelemetry tracing with OTLP exporter when enabled.
"""

from __future__ import annotations

from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_tracer_provider_initialized = False


def setup_tracing(app=None) -> Optional[trace.TracerProvider]:
    """Set up OpenTelemetry tracing.

    Args:
        app: Optional FastAPI app to instrument

    Returns:
        The TracerProvider if tracing is enabled, None otherwise
    """
    global _tracer_provider_initialized

    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry tracing is disabled")
        return None

    if _tracer_provider_initialized:
        logger.warning("OpenTelemetry tracing already initialized")
        return trace.get_tracer_provider()

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
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

    provider = TracerProvider(resource=resource)

    otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    if otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=settings.OTEL_EXPORTER_OTLP_HEADERS or {},
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        logger.info(f"OpenTelemetry OTLP exporter configured: {otlp_endpoint}")
    else:
        logger.warning(
            "OTEL_ENABLED=true but OTEL_EXPORTER_OTLP_ENDPOINT not set; "
            "no spans will be exported"
        )

    trace.set_tracer_provider(provider)
    _tracer_provider_initialized = True

    if app is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info("FastAPI instrumentation enabled")

    logger.info("OpenTelemetry tracing initialized")
    return provider


def shutdown_tracing():
    """Shut down OpenTelemetry tracing."""
    global _tracer_provider_initialized

    if not _tracer_provider_initialized:
        return

    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()

    _tracer_provider_initialized = False
    logger.info("OpenTelemetry tracing shut down")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer by name.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        An OpenTelemetry Tracer instance
    """
    return trace.get_tracer(name)


__all__ = ["setup_tracing", "shutdown_tracing", "get_tracer"]
