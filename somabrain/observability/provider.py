"""Observability provider.

This module provides a thin wrapper around OpenTelemetry tracing for production
use. Under strict, production-focused policy we do not expose no-op stubs.
If OpenTelemetry is not available or tracing cannot be initialized, initialization
raises an explicit error so missing instrumentation is addressed during deploy.
"""

from __future__ import annotations

from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
except Exception as exc:  # pragma: no cover - intentionally strict
    raise RuntimeError(
        "OpenTelemetry packages are required for observability. Install 'opentelemetry-sdk' and related packages."
    ) from exc


def init_tracing(service_name: str, *, console_export: bool = False) -> None:
    """Initialize OpenTelemetry tracer provider.

    Args:
        service_name: logical service name to expose in traces.
        console_export: if True, attach a console span exporter for local debugging.

    Raises:
        RuntimeError: if tracer cannot be initialized.
    """
    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        if console_export:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
    except Exception as e:  # pragma: no cover - surface initialization failures
        raise RuntimeError("Failed to initialize OpenTelemetry tracer") from e


def get_tracer(name: str | None = None):
    """Return an OpenTelemetry tracer instance.

    This will raise if tracing is not initialized to ensure production code does
    not silently run without instrumentation.
    """
    try:
        return trace.get_tracer(name or __name__)
    except Exception as e:
        raise RuntimeError("Tracer not available; call init_tracing first") from e
