"""Metrics Middleware and Endpoint for SomaBrain.

This module provides Django Ninja integration for metrics:
- metrics_endpoint: Prometheus metrics exposition endpoint
- timing_middleware: Automatic request timing middleware
- External metrics scraping helpers
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Callable, Iterable

from somabrain.metrics.core import (
    CONTENT_TYPE_LATEST,
    HTTP_COUNT,
    HTTP_LATENCY,
    generate_latest,
    get_gauge,
    registry,
)


# ---------------------------------------------------------------------------
# External Metrics Scraping
# ---------------------------------------------------------------------------

_external_metrics_lock = Lock()
_external_metrics_scraped: dict[str, float] = {}
_DEFAULT_EXTERNAL_METRICS = ("kafka", "postgres", "opa")

EXTERNAL_METRICS_SCRAPE_STATUS = get_gauge(
    "somabrain_external_metrics_scraped",
    "Flag indicating that an external exporter has been scraped at least once",
    ["source"],
)


def mark_external_metric_scraped(source: str) -> None:
    """Mark an external exporter as scraped for readiness gating."""
    if not source:
        return
    label = str(source).strip().lower()
    if not label:
        return
    now = time.time()
    with _external_metrics_lock:
        _external_metrics_scraped[label] = now
    try:
        EXTERNAL_METRICS_SCRAPE_STATUS.labels(source=label).set(1)
    except Exception:
        pass


def external_metrics_ready(
    required: Iterable[str] | None = None, freshness_seconds: float | None = None
) -> bool:
    """Return True if all required exporters have reported a recent scrape."""
    targets = (
        [str(s).strip().lower() for s in required]
        if required is not None
        else list(_DEFAULT_EXTERNAL_METRICS)
    )
    now = time.time()
    with _external_metrics_lock:
        snapshot = dict(_external_metrics_scraped)
    for label in targets:
        if not label:
            continue
        ts = snapshot.get(label)
        if ts is None:
            return False
        if freshness_seconds is not None and now - ts > freshness_seconds:
            return False
    return True


def reset_external_metrics(sources: Iterable[str] | None = None) -> None:
    """Reset tracked scrape state for the provided sources (or all)."""
    if sources is None:
        with _external_metrics_lock:
            targets = list(_external_metrics_scraped.keys())
            _external_metrics_scraped.clear()
    else:
        targets = [str(s).strip().lower() for s in sources if str(s).strip()]
        with _external_metrics_lock:
            for label in targets:
                _external_metrics_scraped.pop(label, None)
    for label in targets:
        if not label:
            continue
        try:
            EXTERNAL_METRICS_SCRAPE_STATUS.labels(source=label).set(0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Django Integration
# ---------------------------------------------------------------------------


def metrics_endpoint(request: Any) -> HttpResponse:
    """
    Django view for exposing Prometheus metrics.

    Returns the current metrics in Prometheus exposition format.
    This endpoint can be scraped by Prometheus servers for monitoring.

    Returns:
        Response: Django Ninja response with metrics data in Prometheus format.

    Example:
        >>> # Access via: GET /metrics
        >>> response = await metrics_endpoint()
        >>> print(response.media_type)  # 'text/plain; version=0.0.4; charset=utf-8'
    """
    from django.http import HttpResponse

    # Export only real counters from the shared registry – no synthetic increments.
    try:
        data = generate_latest(registry)
    except Exception:
        data = b""
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)


class PrometheusTimingMiddleware:
    """
    Django middleware for automatic request timing and metrics collection.

    Intercepts all HTTP requests to measure latency and count requests by method,
    path, and status code. Automatically updates Prometheus metrics.
    """

    def __init__(self, get_response: Callable[[Any], Any]):
        """Initialize the instance."""

        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Execute call  .

        Args:
            request: The request.
        """

        start = time.perf_counter()
        response = self.get_response(request)

        elapsed = max(0.0, time.perf_counter() - start)
        path = request.path
        method = request.method

        try:
            HTTP_LATENCY.labels(method=method, path=path).observe(elapsed)
            status = str(response.status_code)
            HTTP_COUNT.labels(method=method, path=path, status=status).inc()
        except Exception:
            pass

        return response


__all__ = [
    # External metrics
    "EXTERNAL_METRICS_SCRAPE_STATUS",
    "mark_external_metric_scraped",
    "external_metrics_ready",
    "reset_external_metrics",
    # Django integration
    "metrics_endpoint",
    "PrometheusTimingMiddleware",
]
