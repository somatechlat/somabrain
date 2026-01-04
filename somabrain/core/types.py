"""Shared type definitions for SomaBrain.

This module provides common type aliases and protocols used throughout
the codebase to ensure consistent typing and enable dependency injection.
"""

from __future__ import annotations

from typing import Protocol, Union, runtime_checkable

import numpy as np
from numpy.typing import NDArray

# Type aliases for common array types
ArrayLike = Union[np.ndarray, list, tuple]
Vector = NDArray[np.floating]
FloatArray = NDArray[np.float32]
Float64Array = NDArray[np.float64]


@runtime_checkable
class MetricsInterface(Protocol):
    """Protocol for metrics recording.

    This interface allows metrics to be injected without creating
    circular import dependencies. Components depend on this protocol
    rather than concrete metrics implementations.
    """

    def inc_counter(
        self, name: str, labels: dict[str, str] | None = None, value: float = 1.0
    ) -> None:
        """Increment a counter metric."""
        ...

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record an observation in a histogram."""
        ...

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge metric value."""
        ...


class NullMetrics:
    """No-op metrics implementation for testing and fallback.

    This implementation satisfies MetricsInterface but performs no operations,
    useful for testing or when metrics are disabled.
    """

    def inc_counter(
        self, name: str, labels: dict[str, str] | None = None, value: float = 1.0
    ) -> None:
        """Execute inc counter.

        Args:
            name: The name.
            labels: The labels.
            value: The value.
        """

        pass

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Execute observe histogram.

        Args:
            name: The name.
            value: The value.
            labels: The labels.
        """

        pass

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Set gauge.

        Args:
            name: The name.
            value: The value.
            labels: The labels.
        """

        pass


# Singleton null metrics instance
NULL_METRICS = NullMetrics()
