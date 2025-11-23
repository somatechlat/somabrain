"""Somabrain error hierarchy.

All production code should raise one of the concrete subclasses defined here
instead of using bare ``Exception`` or silent ``pass``.  The hierarchy is
designed to be explicit (VIBE *Error‑first*) and to carry optional ``cause``
information for debugging.
"""

from __future__ import annotations

from typing import Optional


class SomabrainError(RuntimeError):
    """Base class for all domain‑specific errors.

    ``code`` can be used by callers (e.g., API error handling) to map to a
    stable identifier.  ``cause`` preserves the original exception for stack
    traces.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.__cause__ = cause


class ConfigError(SomabrainError):
    """Raised when required configuration is missing or malformed."""


class InvariantError(SomabrainError):
    """Raised when a logical invariant is violated at runtime."""


class ExternalError(SomabrainError):
    """Wraps errors from downstream services (Kafka, Postgres, Redis, etc.)."""
