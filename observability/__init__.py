"""Module __init__."""

from .provider import init_tracing, get_tracer  # noqa: F401
from common.logging import logger  # noqa: F401

"""Observability package public surface.

Strict mode: expose only the tracing initializer and tracer accessor.
Tests and services import ``observability.provider``; we forward to the
implementation while avoiding any implicit alternative stubs.
"""


__all__ = ["init_tracing", "get_tracer"]