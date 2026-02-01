"""HTTP Helper Functions for Memory Client.

This module provides HTTP request/response handling utilities for the
MemoryClient, including retry logic and metrics recording.

Per Requirements H1.1-H1.5 (End-to-End Tracing):
- H1.1: Injects trace context (traceparent, tracestate) into HTTP headers
- H1.2: Creates child spans for SFM operations
- H1.3: Propagates trace context for distributed tracing
- H1.4: Records errors in spans with stack traces
- H1.5: Supports configurable sampling rate (default 1%)

Functions:
- inject_trace_context: Inject OpenTelemetry trace context into headers
- record_http_metrics: Record HTTP operation metrics
- http_post_with_retries_sync: Synchronous POST with retries
- http_post_with_retries_async: Async POST with retries
- store_http_sync: Store memory via HTTP (sync)
- store_http_async: Store memory via HTTP (async)
- store_bulk_http_sync: Bulk store via HTTP (sync)
- store_bulk_http_async: Bulk store via HTTP (async)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Tuple

from somabrain import metrics as M

if TYPE_CHECKING:
    from somabrain.apps.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject OpenTelemetry trace context into HTTP headers.

    Per Requirements H1.1-H1.3:
    - H1.1: Injects traceparent and tracestate headers
    - H1.2: Uses W3C Trace Context format for interoperability
    - H1.3: Enables distributed tracing across SB→SFM calls

    Args:
        headers: Existing headers dict to inject trace context into.

    Returns:
        Headers dict with trace context injected (modifies in place and returns).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.propagate import inject

        # Get current span context and inject into headers
        # This adds traceparent and tracestate headers per W3C Trace Context spec
        inject(headers)

        # Log trace ID for debugging (only if we have an active span)
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            span_context = current_span.get_span_context()
            if span_context.is_valid:
                logger.debug(
                    "Injected trace context",
                    trace_id=format(span_context.trace_id, "032x"),
                    span_id=format(span_context.span_id, "016x"),
                )
    except ImportError:
        # OpenTelemetry not installed - skip trace injection
        logger.debug("OpenTelemetry not available, skipping trace injection")
    except Exception as exc:
        # Don't fail the request if tracing fails
        logger.debug(f"Failed to inject trace context: {exc}")

    return headers


def _start_span(operation: str, tenant: str, endpoint: str) -> Any:
    """Start an OpenTelemetry span for an HTTP operation.

    Per Requirements H1.2, H1.4:
    - H1.2: Creates child span with operation name
    - H1.4: Span will record errors if operation fails

    Args:
        operation: Operation name (e.g., 'remember', 'recall')
        tenant: Tenant identifier
        endpoint: API endpoint being called

    Returns:
        Span context manager or None if tracing unavailable.
    """
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("soma.memory_client")
        span = tracer.start_span(
            f"sb_sfm_{operation}",
            attributes={
                "tenant": tenant,
                "endpoint": endpoint,
                "service.name": "somabrain",
                "peer.service": "somafractalmemory",
            },
        )
        return span
    except ImportError:
        return None
    except Exception:
        return None


def _end_span(
    span: Any,
    success: bool,
    status_code: int,
    error: Exception | None = None,
) -> None:
    """End an OpenTelemetry span with status and optional error.

    Per Requirement H1.4: Records error details and stack trace on failure.

    Args:
        span: The span to end (may be None)
        success: Whether the operation succeeded
        status_code: HTTP status code
        error: Optional exception to record
    """
    if span is None:
        return

    try:
        from opentelemetry.trace import StatusCode

        span.set_attribute("http.status_code", status_code)
        span.set_attribute("success", success)

        if error is not None:
            span.record_exception(error)
            span.set_status(StatusCode.ERROR, str(error))
        elif not success:
            span.set_status(StatusCode.ERROR, f"HTTP {status_code}")
        else:
            span.set_status(StatusCode.OK)

        span.end()
    except Exception:
        # Don't fail if span ending fails
        try:
            span.end()
        except Exception:
            pass


def record_http_metrics(
    operation: str,
    tenant: str,
    success: bool,
    status: int,
    duration: float,
) -> None:
    """Record HTTP operation metrics to Prometheus.

    Args:
        operation: The operation name (e.g., 'remember', 'recall')
        tenant: The tenant identifier
        success: Whether the operation succeeded
        status: HTTP status code
        duration: Operation duration in seconds
    """
    try:
        status_label = str(status or (200 if success else 0))
        M.MEMORY_HTTP_REQUESTS.labels(
            operation=operation, tenant=tenant, status=status_label
        ).inc()
        M.MEMORY_HTTP_LATENCY.labels(operation=operation, tenant=tenant).observe(
            max(0.0, float(duration))
        )
    except Exception:
        pass


def http_post_with_retries_sync(
    transport: "MemoryHTTPTransport",
    endpoint: str,
    body: dict,
    headers: dict,
    tenant: str,
    *,
    max_retries: int = 2,
    operation: str = "unknown",
) -> Tuple[bool, int, Any]:
    """Execute a synchronous HTTP POST with retries, metrics, and tracing.

    Per Requirements H1.1-H1.4:
    - Injects trace context into headers for distributed tracing
    - Creates span for the operation
    - Records errors in span on failure

    Args:
        transport: The HTTP transport instance
        endpoint: API endpoint path
        body: Request body dictionary
        headers: Request headers
        tenant: Tenant identifier for metrics
        max_retries: Maximum retry attempts
        operation: Operation name for metrics

    Returns:
        Tuple of (success, status_code, response_data)
    """
    if transport is None:
        return False, 0, None

    # H1.1: Inject trace context into headers
    headers = inject_trace_context(dict(headers))

    # H1.2: Start span for this operation
    span = _start_span(operation, tenant, endpoint)

    start = time.perf_counter()
    success = False
    status = 0
    data: Any = None
    error: Exception | None = None

    try:
        success, status, data = transport.post_with_retries_sync(
            endpoint, body, headers, max_retries=max_retries
        )
        return success, status, data
    except Exception as exc:
        error = exc
        raise
    finally:
        duration = max(0.0, time.perf_counter() - start)
        record_http_metrics(operation, tenant, success, status, duration)
        # H1.4: End span with status and error if any
        _end_span(span, success, status, error)


async def http_post_with_retries_async(
    transport: "MemoryHTTPTransport",
    endpoint: str,
    body: dict,
    headers: dict,
    tenant: str,
    *,
    max_retries: int = 2,
    operation: str = "unknown",
) -> Tuple[bool, int, Any]:
    """Execute an async HTTP POST with retries, metrics, and tracing.

    Per Requirements H1.1-H1.4:
    - Injects trace context into headers for distributed tracing
    - Creates span for the operation
    - Records errors in span on failure

    Args:
        transport: The HTTP transport instance
        endpoint: API endpoint path
        body: Request body dictionary
        headers: Request headers
        tenant: Tenant identifier for metrics
        max_retries: Maximum retry attempts
        operation: Operation name for metrics

    Returns:
        Tuple of (success, status_code, response_data)
    """
    if transport is None:
        return False, 0, None

    # H1.1: Inject trace context into headers
    headers = inject_trace_context(dict(headers))

    # H1.2: Start span for this operation
    span = _start_span(operation, tenant, endpoint)

    start = time.perf_counter()
    success = False
    status = 0
    data: Any = None
    error: Exception | None = None

    try:
        success, status, data = await transport.post_with_retries_async(
            endpoint, body, headers, max_retries=max_retries
        )
        return success, status, data
    except Exception as exc:
        error = exc
        raise
    finally:
        duration = max(0.0, time.perf_counter() - start)
        record_http_metrics(operation, tenant, success, status, duration)
        # H1.4: End span with status and error if any
        _end_span(span, success, status, error)


def store_http_sync(
    transport: "MemoryHTTPTransport",
    body: dict,
    headers: dict,
    tenant: str,
) -> Tuple[bool, Any]:
    """POST a memory to the HTTP memory service (sync).

    The service's OpenAPI defines the endpoint ``POST /memories`` with a
    ``MemoryStoreRequest`` payload.

    Args:
        transport: The HTTP transport instance
        body: Memory payload
        headers: Request headers
        tenant: Tenant identifier for metrics

    Returns:
        Tuple of (success, response_data)
    """
    if transport is None:
        return False, None

    success, _, data = http_post_with_retries_sync(
        transport, "/memories", body, headers, tenant, operation="remember"
    )
    if success:
        return True, data
    return False, data


async def store_http_async(
    transport: "MemoryHTTPTransport",
    body: dict,
    headers: dict,
    tenant: str,
) -> Tuple[bool, Any]:
    """POST a memory to the HTTP memory service (async).

    Args:
        transport: The HTTP transport instance
        body: Memory payload
        headers: Request headers
        tenant: Tenant identifier for metrics

    Returns:
        Tuple of (success, response_data)
    """
    if transport is None:
        return False, None

    # VIBE FIX: Reverted double-wrapping (Async)
    # remember.py already formats data correctly.

    success, _, data = await http_post_with_retries_async(
        transport, "/memories", body, headers, tenant, operation="remember"
    )
    if success:
        return True, data
    return False, data


def store_bulk_http_sync(
    transport: "MemoryHTTPTransport",
    batch_request: dict,
    headers: dict,
    tenant: str,
) -> Tuple[bool, int, Any]:
    """Store multiple memories by iterating over items (sync).

    The memory service API does not provide a batch endpoint. This method
    iterates over the items in the batch request and stores each one
    individually via POST /memories.

    Args:
        transport: The HTTP transport instance
        batch_request: Batch request with 'items' list
        headers: Request headers
        tenant: Tenant identifier for metrics

    Returns:
        Tuple of (all_success, status_code, response_dict)
    """
    if transport is None:
        return False, 0, None
    items = batch_request.get("items", [])
    if not items:
        return False, 0, None
    results = []
    all_success = True
    for idx, item in enumerate(items):
        item_headers = dict(headers)
        item_headers["X-Request-ID"] = f"{headers.get('X-Request-ID', 'bulk')}:{idx}"
        success, data = store_http_sync(transport, item, item_headers, tenant)
        results.append(data if success else None)
        if not success:
            all_success = False
    return all_success, 200 if all_success else 500, {"items": results}


async def store_bulk_http_async(
    transport: "MemoryHTTPTransport",
    batch_request: dict,
    headers: dict,
    tenant: str,
) -> Tuple[bool, int, Any]:
    """Store multiple memories by iterating over items (async).

    Args:
        transport: The HTTP transport instance
        batch_request: Batch request with 'items' list
        headers: Request headers
        tenant: Tenant identifier for metrics

    Returns:
        Tuple of (all_success, status_code, response_dict)
    """
    if transport is None:
        return False, 0, None
    items = batch_request.get("items", [])
    if not items:
        return False, 0, None
    results = []
    all_success = True
    for idx, item in enumerate(items):
        item_headers = dict(headers)
        item_headers["X-Request-ID"] = f"{headers.get('X-Request-ID', 'bulk')}:{idx}"
        success, data = await store_http_async(transport, item, item_headers, tenant)
        results.append(data if success else None)
        if not success:
            all_success = False
    return all_success, 200 if all_success else 500, {"items": results}


__all__ = [
    "inject_trace_context",
    "record_http_metrics",
    "http_post_with_retries_sync",
    "http_post_with_retries_async",
    "store_http_sync",
    "store_http_async",
    "store_bulk_http_sync",
    "store_bulk_http_async",
]
