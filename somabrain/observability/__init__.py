"""Module __init__."""

from .provider import get_tracer, init_tracing  # re-export for convenience

__all__ = ["init_tracing", "get_tracer"]
