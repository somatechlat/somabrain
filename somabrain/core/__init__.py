"""SomaBrain Core Modules - Validation, error handling, logging, and scoring.

This module provides foundational components for the SomaBrain system:
    - container: Dependency injection container for runtime singletons
    - exceptions: Custom exception hierarchy
    - types: Shared type definitions and protocols
    - validation: Input validation utilities
    - logging_setup: Logging configuration
"""

from .container import Container, container
from .exceptions import (
    CircuitBreakerOpen,
    CognitiveError,
    ConfigurationError,
    HRRError,
    MemorySerializationError,
    MemoryServiceError,
    MemoryTimeoutError,
    QuotaExceededError,
    SDRError,
    SomaBrainError,
    TenantError,
    TenantNotFoundError,
    ValidationError,
)
from .types import (
    ArrayLike,
    Float64Array,
    FloatArray,
    MetricsInterface,
    NullMetrics,
    NULL_METRICS,
    Vector,
)

__all__ = [
    # Container
    "Container",
    "container",
    # Exceptions
    "SomaBrainError",
    "ConfigurationError",
    "ValidationError",
    "MemoryServiceError",
    "CircuitBreakerOpen",
    "MemoryTimeoutError",
    "MemorySerializationError",
    "CognitiveError",
    "HRRError",
    "SDRError",
    "TenantError",
    "TenantNotFoundError",
    "QuotaExceededError",
    # Types
    "ArrayLike",
    "Vector",
    "FloatArray",
    "Float64Array",
    "MetricsInterface",
    "NullMetrics",
    "NULL_METRICS",
]