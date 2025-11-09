"""Lightweight OpenTelemetry wrapper for SomaBrain.

Provides a minimal span context manager. If OpenTelemetry isn't installed
this module degrades to no-op spans so calls are safe in tests and CI.
"""

from contextlib import contextmanager

try:  # pragma: no cover - runtime optional
    from opentelemetry import trace  # type: ignore

    _tracer = trace.get_tracer(__name__)
    OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when package missing
    _tracer = None
    OTEL_AVAILABLE = False


@contextmanager
def span(name: str, **attrs):
    """Return a span context manager.

    Usage:
        with span("memory.search", query=q):
            ...
    """
    if OTEL_AVAILABLE and _tracer is not None:
        with _tracer.start_as_current_span(name) as s:
            for k, v in attrs.items():
                try:
                    s.set_attribute(k, v)
                except Exception:
                    pass
            yield s
    else:
        # no-op dummy object
        class _Dummy:
            def set_attribute(self, k, v):
                return None

        yield _Dummy()
