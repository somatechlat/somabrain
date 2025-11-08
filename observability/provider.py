"""Top‑level no‑op observability provider used for unit tests.

The production code expects ``observability.provider`` to expose ``init_tracing``
and ``get_tracer`` (returning an object with ``start_as_current_span``).  This
module implements a minimal stub that does nothing but satisfies the API, so
imports succeed in the test environment.
"""

from __future__ import annotations

from typing import Any


def init_tracing() -> None:
    """No‑op tracing initializer for tests."""


class _NoOpSpan:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _NoOpTracer:
    def start_as_current_span(self, name: str) -> _NoOpSpan:
        return _NoOpSpan(name)


def get_tracer(name: str) -> _NoOpTracer:  # pragma: no cover
    return _NoOpTracer()
"""Minimal no‑op tracing provider used for unit tests.

The production code imports ``observability.provider`` for OpenTelemetry
instrumentation.  In the test environment the ``observability`` package may not be
installed, which caused ``ModuleNotFoundError`` during test collection.  This
module implements a tiny stub that satisfies the expected API:

* ``init_tracing()`` – a no‑op placeholder.
* ``get_tracer(name)`` – returns a ``_NoOpTracer`` instance.
* ``_NoOpTracer.start_as_current_span(name)`` – context manager that does
  nothing but allows ``with tracer.start_as_current_span(...):`` syntax.

The implementation deliberately avoids any external dependencies, keeping the
runtime footprint minimal while preserving the original code paths.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator


def init_tracing() -> None:
    """Initialize tracing infrastructure.

    In production this would configure OpenTelemetry exporters.  For the test
    suite we simply provide a no‑op implementation.
    """


class _NoOpSpan:
    """A dummy span that does nothing on exit."""

    def __init__(self, name: str):
        self.name = name

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        # No cleanup required.
        return None


class _NoOpTracer:
    """Tracer exposing ``start_as_current_span`` compatible with OpenTelemetry."""

    def start_as_current_span(self, name: str) -> _NoOpSpan:
        return _NoOpSpan(name)


def get_tracer(name: str) -> _NoOpTracer:  # pragma: no cover – exercised via imports
    """Return a no‑op tracer instance.

    The ``name`` argument is accepted for API compatibility but ignored.
    """

    return _NoOpTracer()
"""OpenTelemetry provider initializer for SomaBrain.

This module is intentionally lightweight and safe to import when OpenTelemetry
packages are not installed. It reads environment variables to configure a
TracerProvider and (optionally) a MeterProvider. When the SDK isn't available
it returns no-op tracer/meter objects.

Env vars supported:
- SOMABRAIN_OTEL_SERVICE_NAME (default: somabrain)
- SOMABRAIN_OTLP_ENDPOINT (optional, if provided an OTLP exporter is configured)
- SOMABRAIN_OTEL_SAMPLER (optional, "always_on"|"always_off"|"parent_based_traceidratio")
- SOMABRAIN_OTEL_TRACE_RATIO (float 0..1 used when sampler is traceidratio)

Usage:
    from observability.provider import get_tracer, init_tracing
    init_tracing()  # idempotent
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("op"):
        ...
"""

import os

def _env_true(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return v.strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return default

# Provide safe defaults when opentelemetry is not installed
try:  # pragma: no cover - optional dependency
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - fallback
    trace = None
    metrics = None
    TracerProvider = None
    MeterProvider = None
    OTLPSpanExporter = None
    OTLPMetricExporter = None
    OTEL_AVAILABLE = False


_tracer_provider_initialized = False
_REQUIRE_TRACING = _env_true("SOMABRAIN_REQUIRE_TRACING", False)
_ALLOW_NOOP_TRACING = _env_true("SOMABRAIN_ALLOW_NOOP_TRACING", False)


def _parse_sampler():
    sval = os.getenv("SOMABRAIN_OTEL_SAMPLER", "always_on").lower()
    if sval == "always_on":
        return None
    if sval == "always_off":
        return None
    # trace ratio handling is left to user-provided policies for now
    return None


def init_tracing():
    """Initialize tracing and metrics providers based on environment variables.

    This is idempotent.
    """
    global _tracer_provider_initialized
    if _tracer_provider_initialized:
        return

    service_name = os.getenv("SOMABRAIN_OTEL_SERVICE_NAME", "somabrain")
    otlp = os.getenv("SOMABRAIN_OTLP_ENDPOINT")

    if not OTEL_AVAILABLE:
        if _REQUIRE_TRACING and not _ALLOW_NOOP_TRACING:
            raise RuntimeError(
                "Tracing required but OpenTelemetry SDK not available. Install and configure OTel or unset SOMABRAIN_REQUIRE_TRACING."
            )
        _tracer_provider_initialized = True
        return

    resource = Resource.create({"service.name": service_name})
    tp = TracerProvider(resource=resource)

    # configure OTLP exporter if endpoint provided
    if otlp:
        try:
            exporter = OTLPSpanExporter(endpoint=otlp)
            tp.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            # fallback to console exporter on error
            tp.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        tp.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tp)

    # metrics (optional)
    try:
        if OTLPMetricExporter is not None and otlp:
            me = MeterProvider(resource=resource)
            metrics.set_meter_provider(me)
    except Exception:
        pass

    _tracer_provider_initialized = True


def get_tracer(name: str):
    """Return a tracer. If OTel is unavailable return a no-op tracer-like object."""
    if OTEL_AVAILABLE and trace is not None:
        return trace.get_tracer(name)

    # No-op tracer replacement
    if _REQUIRE_TRACING and not _ALLOW_NOOP_TRACING:
        raise RuntimeError(
            "Tracing required (SOMABRAIN_REQUIRE_TRACING=1) but OpenTelemetry is unavailable."
        )
    class _NoopSpan:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_attribute(self, k, v):
            return None

    class _NoopTracer:
        def start_as_current_span(self, name, **kwargs):
            return _NoopSpan()

    return _NoopTracer()
