"""Observability package public surface.

Strict mode: expose only the tracing initializer and tracer accessor.
Tests and services import ``observability.provider``; we forward to the
implementation while avoiding any implicit alternative stubs.
"""

from .provider import init_tracing, get_tracer  # noqa: F401

__all__ = ["init_tracing", "get_tracer"]
