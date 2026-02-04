"""Core Metrics Infrastructure for SomaBrain.

This module provides the foundational metrics infrastructure including:
- Shared Prometheus registry
- Metric factory functions (_counter, _gauge, _histogram, _summary)
- Public getter functions (get_counter, get_gauge, get_histogram)
- Core HTTP and system metrics

All other metrics modules should import from here to ensure consistent
registry usage and avoid duplicate metric registration.
"""

from __future__ import annotations

import builtins as _builtins
from typing import Any, Protocol

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry,
        generate_latest,
    )
    from prometheus_client import (
        Counter as _PromCounter,
    )
    from prometheus_client import (
        Gauge as _PromGauge,
    )
    from prometheus_client import (
        Histogram as _PromHistogram,
    )
    from prometheus_client import (
        Summary as _PromSummary,
    )
except Exception as e:  # pragma: no cover
    raise ImportError(
        f"prometheus_client is required for somabrain.metrics (strict mode). Missing dependency: {e}"
    )


# ---------------------------------------------------------------------------
# Type helpers for static analysis
# ---------------------------------------------------------------------------


class _MetricProtocol(Protocol):
    """Minimal protocol representing a Prometheus metric used in the code.

    All concrete metric objects expose ``labels`` (returning a metric with the
    same interface) and one of ``inc``, ``set`` or ``observe`` depending on the
    metric type. The protocol captures the superset of those methods so the
    type‑checker can validate calls such as ``metric.labels(...).inc()``.
    """

    def labels(self, *args: Any, **kwargs: Any) -> "_MetricProtocol":
        """Execute labels."""
        ...

    def inc(self, amount: float = 1) -> None:  # noqa: D401
        """Execute inc.

        Args:
            amount: The amount.
        """
        ...

    def set(self, value: float) -> None:
        """Execute set.

        Args:
            value: The value.
        """
        ...

    def observe(self, value: float) -> None:
        """Execute observe.

        Args:
            value: The value.
        """
        ...


# ---------------------------------------------------------------------------
# Shared Registry
# ---------------------------------------------------------------------------

# Share a single registry across module reloads/process components.
try:
    _reg = getattr(_builtins, "_SOMABRAIN_METRICS_REGISTRY")
except Exception:
    _reg = None
if not _reg:
    _reg = CollectorRegistry()
    try:
        setattr(_builtins, "_SOMABRAIN_METRICS_REGISTRY", _reg)
    except Exception:
        pass
registry = _reg


def _get_existing(name: str) -> Any:
    """Check if a metric with the given name already exists in the registry."""
    try:
        return registry._names_to_collectors.get(name)
    except Exception:
        try:
            return REGISTRY._names_to_collectors.get(name)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Metric Factory Functions
# ---------------------------------------------------------------------------


def _counter(
    name: str, documentation: str, *args: Any, **kwargs: Any
) -> _MetricProtocol:
    """Create or retrieve a Counter metric."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromCounter(name, documentation, *args, **kwargs)


def _gauge(name: str, documentation: str, *args: Any, **kwargs: Any) -> _MetricProtocol:
    """Create or retrieve a Gauge metric."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromGauge(name, documentation, *args, **kwargs)


def _histogram(
    name: str, documentation: str, *args: Any, **kwargs: Any
) -> _MetricProtocol:
    """Create or retrieve a Histogram metric."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromHistogram(name, documentation, *args, **kwargs)


def _summary(
    name: str, documentation: str, *args: Any, **kwargs: Any
) -> _MetricProtocol:
    """Create or retrieve a Summary metric."""
    existing = _get_existing(name)
    if existing is not None:
        return existing
    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromSummary(name, documentation, *args, **kwargs)


# Public aliases for metric types
Counter = _counter
Gauge = _gauge
Histogram = _histogram
Summary = _summary


# ---------------------------------------------------------------------------
# Public Getter Functions
# ---------------------------------------------------------------------------


def get_counter(
    name: str, documentation: str, labelnames: list[str] | None = None
) -> _MetricProtocol:
    """Get or create a Counter in the central registry.

    Returns an existing collector if already registered, otherwise creates and
    registers a new Counter attached to the central `registry`.
    """
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _counter(name, documentation, labelnames, registry=registry)
    return _counter(name, documentation, registry=registry)


def get_gauge(
    name: str, documentation: str, labelnames: list[str] | None = None
) -> _MetricProtocol:
    """Get or create a Gauge in the central registry."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _gauge(name, documentation, labelnames, registry=registry)
    return _gauge(name, documentation, registry=registry)


def get_histogram(
    name: str,
    documentation: str,
    labelnames: list[str] | None = None,
    **kwargs: Any,
) -> _MetricProtocol:
    """Get or create a Histogram in the central registry."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _histogram(name, documentation, labelnames, registry=registry, **kwargs)
    return _histogram(name, documentation, registry=registry, **kwargs)


def get_summary(
    name: str,
    documentation: str,
    labelnames: list[str] | None = None,
    **kwargs: Any,
) -> _MetricProtocol:
    """Get or create a Summary in the central registry."""
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _summary(name, documentation, labelnames, registry=registry, **kwargs)
    return _summary(name, documentation, registry=registry, **kwargs)


# ---------------------------------------------------------------------------
# Core HTTP Metrics
# ---------------------------------------------------------------------------

HTTP_COUNT = Counter(
    "somabrain_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)

HTTP_LATENCY = Histogram(
    "somabrain_http_latency_seconds",
    "HTTP request latency",
    ["method", "path"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Legacy tau_gauge - kept in core to avoid circular imports
# ---------------------------------------------------------------------------

if "soma_context_builder_tau" in REGISTRY._names_to_collectors:
    tau_gauge = REGISTRY._names_to_collectors["soma_context_builder_tau"]
else:
    tau_gauge = Gauge(
        "soma_context_builder_tau",
        "Current tau value for diversity adaptation",
        ["tenant_id"],
        registry=REGISTRY,
    )

# Legacy next-event regret gauge
soma_next_event_regret = get_gauge(
    "soma_next_event_regret",
    "Instantaneous next-event regret (0-1)",
    labelnames=["tenant_id"],
)

# Re-export prometheus_client items needed by other modules
__all__ = [
    # Protocol
    "_MetricProtocol",
    # Registry
    "registry",
    "REGISTRY",
    "CONTENT_TYPE_LATEST",
    "generate_latest",
    # Factory functions (private)
    "_counter",
    "_gauge",
    "_histogram",
    "_summary",
    "_get_existing",
    # Factory functions (public aliases)
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    # Getter functions
    "get_counter",
    "get_gauge",
    "get_histogram",
    "get_summary",
    # Core metrics
    "HTTP_COUNT",
    "HTTP_LATENCY",
    # Legacy gauges
    "tau_gauge",
    "soma_next_event_regret",
]
