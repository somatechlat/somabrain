"""Strict OpenTelemetry span helper (no no-op fallback)."""

from contextlib import contextmanager
from opentelemetry import trace  # type: ignore


@contextmanager
def span(name: str, **attrs):
    provider = trace.get_tracer_provider()
    # Detect default/uninitialized provider classes that result in no-op spans
    if provider is None or provider.__class__.__name__ in {
        "ProxyTracerProvider",
        "DefaultTracerProvider",
    }:
        raise RuntimeError(
            "OpenTelemetry tracer provider not initialized; call observability.provider.init_tracing()"
        )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as s:
        for k, v in attrs.items():
            try:
                s.set_attribute(k, v)
            except Exception:
                pass
        yield s
