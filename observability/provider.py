"""Minimal stub for ``observability.provider`` used in the test suite.

The production code expects the ``observability.provider`` module to expose
``init_tracing`` and ``get_tracer`` (returning an object with a
``start_as_current_span`` context manager).  For unit tests we provide a no‑op
implementation that satisfies the import without pulling in the heavy
OpenTelemetry dependencies.
"""

from __future__ import annotations

from typing import Any


def init_tracing() -> None:
    """No‑op initializer – does nothing in the test environment."""


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
    """Return a stub tracer; ``name`` is ignored for compatibility."""

    return _NoOpTracer()
