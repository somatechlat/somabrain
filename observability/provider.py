"""OpenTelemetry tracing provider for SomaBrain (strict mode).

This module initializes a real OpenTelemetry TracerProvider and exposes
``init_tracing`` and ``get_tracer``. No no-op alternatives are provided.
If OpenTelemetry is not installed or not configured, initialization fails
fast to enforce mandatory observability.
"""

from __future__ import annotations

from common.config.settings import settings
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)

_initialized: bool = False


def init_tracing(service_name: Optional[str] = None) -> None:
    """Initialize OpenTelemetry tracing with OTLP HTTP exporter.

    Requires the following environment variables (strict):
    - ``OTEL_EXPORTER_OTLP_ENDPOINT``: e.g. ``http://localhost:4318``
    - ``OTEL_SERVICE_NAME`` (or pass via ``service_name``)
    """

    global _initialized
    if _initialized:
        return

    endpoint = settings.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError(
            "OTEL_EXPORTER_OTLP_ENDPOINT is required for tracing (strict mode)"
        )

    svc = (
        service_name
        or settings.getenv("OTEL_SERVICE_NAME")
        or settings.getenv("SERVICE_NAME")
        or ""
    ).strip()
    if not svc:
        raise RuntimeError(
            "OTEL_SERVICE_NAME (or service_name) is required for tracing"
        )

    provider = TracerProvider(resource=Resource.create({"service.name": svc}))
    exporter = OTLPSpanExporter(endpoint=endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer(name: str):
    """Return a real tracer; raises if provider is not initialized."""

    provider = trace.get_tracer_provider()
    # Detect uninitialized/default provider to avoid silent no-ops
    if provider is None or provider.__class__.__name__ in {
        "ProxyTracerProvider",
        "DefaultTracerProvider",
    }:
        raise RuntimeError(
            "TracerProvider not initialized. Call observability.provider.init_tracing() first."
        )
    return trace.get_tracer(name)
