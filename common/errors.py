"""Somabrain error hierarchy — I18N Ready.

All production code should raise one of the concrete subclasses defined here
instead of using bare ``Exception`` or silent ``pass``.  The hierarchy is
designed to be explicit (VIBE *Error‑first*) and to carry optional ``cause``
information for debugging.

VIBE RULE 11: All user-facing text MUST use get_message().
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
        """Initialize the instance."""

        super().__init__(message)
        self.code = code
        self.__cause__ = cause


class ConfigError(SomabrainError):
    """Raised when required configuration is missing or malformed."""

    def __init__(
        self,
        key: str,
        reason: str = "missing",
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initialize config error with I18N support."""
        from common.messages import ErrorCode, get_message

        if reason == "missing":
            message = get_message(ErrorCode.CONFIG_MISSING, key=key)
            code = ErrorCode.CONFIG_MISSING.value
        else:
            message = get_message(ErrorCode.CONFIG_INVALID, key=key, reason=reason)
            code = ErrorCode.CONFIG_INVALID.value

        super().__init__(message, code=code, cause=cause)


class InvariantError(SomabrainError):
    """Raised when a logical invariant is violated at runtime."""


class ExternalError(SomabrainError):
    """Wraps errors from downstream services (Kafka, Postgres, Redis, etc.)."""

    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initialize external error with I18N support."""
        from common.messages import ErrorCode, get_message

        service_codes = {
            "milvus": ErrorCode.MILVUS_UNAVAILABLE,
            "postgres": ErrorCode.POSTGRES_UNAVAILABLE,
            "redis": ErrorCode.REDIS_UNAVAILABLE,
            "kafka": ErrorCode.KAFKA_UNAVAILABLE,
        }

        if service.lower() in service_codes:
            final_message = get_message(service_codes[service.lower()])
            code = service_codes[service.lower()].value
        else:
            final_message = message or f"Service '{service}' unavailable"
            code = "external_error"

        super().__init__(final_message, code=code, cause=cause)


class MemoryError(SomabrainError):
    """Raised when memory operations fail."""

    def __init__(
        self,
        operation: str,
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initialize memory error with I18N support."""
        from common.messages import ErrorCode, get_message

        op_codes = {
            "recall": ErrorCode.MEMORY_RECALL_FAILED,
            "store": ErrorCode.MEMORY_STORE_FAILED,
            "delete": ErrorCode.MEMORY_DELETE_FAILED,
        }

        if operation.lower() in op_codes:
            message = get_message(op_codes[operation.lower()])
            code = op_codes[operation.lower()].value
        else:
            message = f"Memory operation '{operation}' failed"
            code = "memory_error"

        super().__init__(message, code=code, cause=cause)


class CognitiveError(SomabrainError):
    """Raised when cognitive operations fail."""

    def __init__(
        self,
        operation: str,
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Initialize cognitive error with I18N support."""
        from common.messages import ErrorCode, get_message

        op_codes = {
            "learn": ErrorCode.COGNITIVE_LEARN_FAILED,
            "ask": ErrorCode.COGNITIVE_ASK_FAILED,
            "act": ErrorCode.COGNITIVE_ACT_FAILED,
        }

        if operation.lower() in op_codes:
            message = get_message(op_codes[operation.lower()])
            code = op_codes[operation.lower()].value
        else:
            message = f"Cognitive operation '{operation}' failed"
            code = "cognitive_error"

        super().__init__(message, code=code, cause=cause)

