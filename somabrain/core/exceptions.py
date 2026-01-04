"""Custom exception hierarchy for SomaBrain.

This module defines a structured exception hierarchy that provides:
- Clear categorization of error types
- Consistent error handling patterns
- Rich context for debugging and logging

All SomaBrain-specific exceptions inherit from SomaBrainError,
allowing callers to catch all application errors with a single handler.
"""

from __future__ import annotations

from typing import Any


class SomaBrainError(Exception):
    """Base exception for all SomaBrain errors.

    All custom exceptions in the SomaBrain system inherit from this class,
    allowing callers to catch all application-specific errors.

    Attributes:
        message: Human-readable error description
        context: Optional dictionary with additional error context
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Initialize the instance."""

        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return string representation."""

        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} [{ctx_str}]"
        return self.message


class ConfigurationError(SomaBrainError):
    """Configuration is invalid or missing.

    Raised when:
    - Required configuration values are missing
    - Configuration values fail validation
    - Configuration file cannot be parsed
    """


class ValidationError(SomaBrainError):
    """Input validation failed.

    Raised when:
    - Request payload fails schema validation
    - Function arguments are invalid
    - Data constraints are violated
    """


class MemoryServiceError(SomaBrainError):
    """Memory service operation failed.

    Base class for all memory-related errors.
    """


class CircuitBreakerOpen(MemoryServiceError):
    """Circuit breaker is open, service unavailable.

    Raised when the circuit breaker has tripped due to repeated failures
    and the service is temporarily unavailable.

    Attributes:
        reset_after_seconds: Estimated time until circuit breaker resets
    """

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        reset_after_seconds: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the instance."""

        ctx = context or {}
        if reset_after_seconds is not None:
            ctx["reset_after_seconds"] = reset_after_seconds
        super().__init__(message, ctx)
        self.reset_after_seconds = reset_after_seconds


class MemoryTimeoutError(MemoryServiceError):
    """Memory service request timed out."""


class MemorySerializationError(MemoryServiceError):
    """Failed to serialize or deserialize memory payload."""


class CognitiveError(SomaBrainError):
    """Error in cognitive processing components."""


class HRRError(CognitiveError):
    """Error in HRR (Holographic Reduced Representation) operations."""


class SDRError(CognitiveError):
    """Error in SDR (Sparse Distributed Representation) operations."""


class TenantError(SomaBrainError):
    """Tenant-related error."""


class TenantNotFoundError(TenantError):
    """Requested tenant does not exist."""


class QuotaExceededError(TenantError):
    """Tenant has exceeded their quota."""
