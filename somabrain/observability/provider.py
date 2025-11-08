"""Minimal observability provider used for testing.

The real project may configure OpenTelemetry tracing, but the unit‑test suite
only requires the symbols ``init_tracing`` and ``get_tracer`` to exist.  They
are implemented as no‑ops that return a dummy tracer object with the usual
``start_as_current_span`` context manager.

This implementation deliberately avoids external dependencies so that the
package can be imported in the isolated test environment.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator


class _DummySpan:
    """A dummy span that does nothing but can be used as a context manager."""

    def __enter__(self) -> "_DummySpan":  # pragma: no cover
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # pragma: no cover
        # No cleanup required.
        return None


class _DummyTracer:
    """A minimal tracer exposing ``start_as_current_span``.

    The returned object implements the context‑manager protocol but otherwise
    discards all tracing information.
    """

    @contextmanager
    def start_as_current_span(self, name: str) -> Generator[_DummySpan, None, None]:
        # Yield a dummy span; the ``with`` block does nothing.
        yield _DummySpan()


def init_tracing(*_, **__) -> None:
    """Initialize tracing – a no‑op for the test environment.

    The signature accepts arbitrary positional and keyword arguments to match
    the production function.  It simply returns ``None``.
    """

    return None


def get_tracer(*_, **__) -> _DummyTracer:
    """Return a dummy tracer instance.

    The real implementation would return an ``opentelemetry.trace.Tracer``.
    Here we return a lightweight stub that satisfies the methods used in the
    code base (currently only ``start_as_current_span``).
    """

    return _DummyTracer()
