"""
Tests for the OpenTelemetry observability module.
"""

from __future__ import annotations

from app.core.observability.metrics import get_meter, setup_metrics, shutdown_metrics
from app.core.observability.tracing import get_tracer, setup_tracing, shutdown_tracing


class TestTracingDisabled:
    """Tests for tracing when OTEL_ENABLED=False."""

    def test_setup_tracing_disabled(self):
        """setup_tracing returns None when OTEL_ENABLED is False."""
        from app.core.config import settings

        original = settings.OTEL_ENABLED
        settings.OTEL_ENABLED = False
        try:
            result = setup_tracing()
            assert result is None
        finally:
            settings.OTEL_ENABLED = original

    def test_get_tracer_works_without_setup(self):
        """get_tracer returns a tracer even without setup."""
        tracer = get_tracer("test-tracer")
        assert tracer is not None


class TestMetricsDisabled:
    """Tests for metrics when OTEL_ENABLED=False."""

    def test_setup_metrics_disabled(self):
        """setup_metrics returns None when OTEL_ENABLED is False."""
        from app.core.config import settings

        original = settings.OTEL_ENABLED
        settings.OTEL_ENABLED = False
        try:
            result = setup_metrics()
            assert result is None
        finally:
            settings.OTEL_ENABLED = original

    def test_get_meter_works_without_setup(self):
        """get_meter returns a meter even without setup."""
        meter = get_meter("test-meter")
        assert meter is not None


class TestTracingShutdown:
    """Tests for tracing shutdown."""

    def test_shutdown_tracing_noop(self):
        """shutdown_tracing is a no-op when not initialized."""
        shutdown_tracing()  # should not raise


class TestMetricsShutdown:
    """Tests for metrics shutdown."""

    def test_shutdown_metrics_noop(self):
        """shutdown_metrics is a no-op when not initialized."""
        shutdown_metrics()  # should not raise
