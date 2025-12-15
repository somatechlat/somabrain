"""Metrics interface for dependency injection without circular imports.

This module provides a Protocol-based interface for metrics recording that can be
imported without triggering circular dependencies. Services should depend on this
interface rather than importing the concrete metrics module directly.

Design Rationale:
    The main `somabrain.metrics` module imports from `metrics_original.py` which
    has dependencies on many parts of the application. This creates circular import
    issues when services try to import metrics at module level.

    By defining a Protocol interface here, services can:
    1. Import this interface at module level (no circular deps)
    2. Receive the concrete metrics implementation via dependency injection
    3. Fall back to NullMetrics for testing without the full metrics stack

Usage:
    from somabrain.metrics.interface import MetricsInterface, get_metrics

    class MyService:
        def __init__(self, metrics: MetricsInterface = None):
            self._metrics = metrics or get_metrics()

        def do_work(self):
            self._metrics.inc_counter("my_counter")

VIBE Compliance:
    - NullMetrics is a real no-op implementation (not a test double)
    - Protocol-based interface allows duck typing without inheritance
    - Thread-safe singleton pattern for metrics access
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional, Protocol


class MetricsInterface(Protocol):
    """Protocol defining the metrics recording interface.

    This protocol allows services to depend on metrics functionality without
    importing the concrete implementation, avoiding circular dependencies.
    """

    def inc_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name (e.g., "http_requests_total")
            labels: Optional label dict for the metric
            value: Amount to increment (default 1.0)
        """
        ...

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record an observation in a histogram.

        Args:
            name: Histogram name (e.g., "request_latency_seconds")
            value: Value to observe
            labels: Optional label dict for the metric
        """
        ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric value.

        Args:
            name: Gauge name (e.g., "active_connections")
            value: Value to set
            labels: Optional label dict for the metric
        """
        ...

    def get_counter(self, name: str, description: str = "") -> Any:
        """Get or create a counter by name.

        Args:
            name: Counter name
            description: Human-readable description

        Returns:
            Counter object (or no-op equivalent)
        """
        ...

    def get_gauge(self, name: str, description: str = "") -> Any:
        """Get or create a gauge by name.

        Args:
            name: Gauge name
            description: Human-readable description

        Returns:
            Gauge object (or no-op equivalent)
        """
        ...

    def get_histogram(self, name: str, description: str = "") -> Any:
        """Get or create a histogram by name.

        Args:
            name: Histogram name
            description: Human-readable description

        Returns:
            Histogram object (or no-op equivalent)
        """
        ...


class _NoOpMetric:
    """No-op metric that accepts any method call and does nothing."""

    def __getattr__(self, name: str) -> Callable[..., "_NoOpMetric"]:
        return lambda *args, **kwargs: self

    def __call__(self, *args: Any, **kwargs: Any) -> "_NoOpMetric":
        return self


class NullMetrics:
    """No-op metrics implementation for testing and fallback.

    This is a real implementation that simply does nothing (silent no-op).
    Use this when metrics are not available or not needed (e.g., unit tests).
    """

    _noop = _NoOpMetric()

    def inc_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0,
    ) -> None:
        """No-op counter increment."""
        pass

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """No-op histogram observation."""
        pass

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """No-op gauge set."""
        pass

    def get_counter(self, name: str, description: str = "") -> _NoOpMetric:
        """Return no-op counter."""
        return self._noop

    def get_gauge(self, name: str, description: str = "") -> _NoOpMetric:
        """Return no-op gauge."""
        return self._noop

    def get_histogram(self, name: str, description: str = "") -> _NoOpMetric:
        """Return no-op histogram."""
        return self._noop


class PrometheusMetrics:
    """Concrete metrics implementation using Prometheus client.

    This wraps the actual prometheus_client metrics and provides the
    MetricsInterface protocol methods.
    """

    def __init__(self) -> None:
        self._counters: Dict[str, Any] = {}
        self._gauges: Dict[str, Any] = {}
        self._histograms: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def inc_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0,
    ) -> None:
        """Increment a counter metric."""
        try:
            from somabrain.metrics_original import get_counter

            counter = get_counter(name, f"Counter: {name}")
            if labels:
                counter.labels(**labels).inc(value)
            else:
                counter.inc(value)
        except Exception:
            pass  # Metrics are best-effort

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record an observation in a histogram."""
        try:
            from somabrain.metrics_original import get_histogram

            hist = get_histogram(name, f"Histogram: {name}")
            if labels:
                hist.labels(**labels).observe(value)
            else:
                hist.observe(value)
        except Exception:
            pass  # Metrics are best-effort

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Set a gauge metric value."""
        try:
            from somabrain.metrics_original import get_gauge

            gauge = get_gauge(name, f"Gauge: {name}")
            if labels:
                gauge.labels(**labels).set(value)
            else:
                gauge.set(value)
        except Exception:
            pass  # Metrics are best-effort

    def get_counter(self, name: str, description: str = "") -> Any:
        """Get or create a counter by name."""
        try:
            from somabrain.metrics_original import get_counter

            return get_counter(name, description or f"Counter: {name}")
        except Exception:
            return _NoOpMetric()

    def get_gauge(self, name: str, description: str = "") -> Any:
        """Get or create a gauge by name."""
        try:
            from somabrain.metrics_original import get_gauge

            return get_gauge(name, description or f"Gauge: {name}")
        except Exception:
            return _NoOpMetric()

    def get_histogram(self, name: str, description: str = "") -> Any:
        """Get or create a histogram by name."""
        try:
            from somabrain.metrics_original import get_histogram

            return get_histogram(name, description or f"Histogram: {name}")
        except Exception:
            return _NoOpMetric()


# Thread-safe singleton for metrics access
_metrics_instance: Optional[MetricsInterface] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsInterface:
    """Get the global metrics instance.

    Returns PrometheusMetrics if available, NullMetrics otherwise.
    Thread-safe singleton pattern.

    Returns:
        MetricsInterface implementation
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                try:
                    # Try to create PrometheusMetrics
                    _metrics_instance = PrometheusMetrics()
                except Exception:
                    # Fall back to NullMetrics
                    _metrics_instance = NullMetrics()
    return _metrics_instance


def set_metrics(metrics: MetricsInterface) -> None:
    """Set the global metrics instance (for testing).

    Args:
        metrics: MetricsInterface implementation to use
    """
    global _metrics_instance
    with _metrics_lock:
        _metrics_instance = metrics


def reset_metrics() -> None:
    """Reset the global metrics instance (for testing)."""
    global _metrics_instance
    with _metrics_lock:
        _metrics_instance = None


__all__ = [
    "MetricsInterface",
    "NullMetrics",
    "PrometheusMetrics",
    "get_metrics",
    "set_metrics",
    "reset_metrics",
]
