"""Module __init__."""

from .provider import init_tracing, get_tracer  # re-export for convenience

__all__ = ["init_tracing", "get_tracer"]