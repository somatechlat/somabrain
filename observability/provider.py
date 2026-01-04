"""OpenTelemetry tracing provider for SomaBrain (strict mode).

This module initializes a real OpenTelemetry TracerProvider and exposes
``init_tracing`` and ``get_tracer``. No no-op alternatives are provided.
If OpenTelemetry is not installed or not configured, initialization fails
fast to enforce mandatory observability.

VIBE Compliance:
    - Uses DI container for initialization state instead of module-level global
    - Thread-safe via DI container
    - Explicit lifecycle management
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass
class TracingState:
    """Tracks tracing initialization state.

    VIBE Compliance:
        - Managed via DI container instead of module-level global
        - Explicit state tracking for idempotent initialization
    """

    initialized: bool = False


def _get_tracing_state() -> TracingState:
    """Get tracing state from DI container."""
    from somabrain.core.container import container

    if not container.has("tracing_state"):
        container.register("tracing_state", TracingState)
    return container.get("tracing_state")


def init_tracing(service_name: Optional[str] = None) -> None:
    """Initialize OpenTelemetry tracing with OTLP HTTP exporter.

    Requires the following environment variables (strict):
    - ``OTEL_EXPORTER_OTLP_ENDPOINT``: e.g. ``http://localhost:4318``
    - ``OTEL_SERVICE_NAME`` (or pass via ``service_name``)

    VIBE Compliance:
        - Uses DI container for initialization state
        - Idempotent - safe to call multiple times
    """
    state = _get_tracing_state()
    if state.initialized:
        return

    endpoint = settings.otel_exporter_otlp_endpoint.strip()
    if not endpoint:
        raise RuntimeError(
            "OTEL_EXPORTER_OTLP_ENDPOINT is required for tracing (strict mode)"
        )

    svc = (
        service_name or settings.otel_service_name or settings.service_name or ""
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
    state.initialized = True


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