"""HTTP Helper Functions for Memory Client.

This module provides HTTP request/response handling utilities for the
MemoryClient, including retry logic and metrics recording.

Functions:
- record_http_metrics: Record HTTP operation metrics
- http_post_with_retries_sync: Synchronous POST with retries
- http_post_with_retries_async: Async POST with retries
- store_http_sync: Store memory via HTTP (sync)
- store_http_async: Store memory via HTTP (async)
- store_bulk_http_sync: Bulk store via HTTP (sync)
- store_bulk_http_async: Bulk store via HTTP (async)
"""

from __future__ import annotations

import time
from typing import Any, Optional, Tuple, TYPE_CHECKING

from somabrain import metrics as M

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport


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
    """Execute a synchronous HTTP POST with retries and metrics.
    
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
    start = time.perf_counter()
    success = False
    status = 0
    data: Any = None
    try:
        success, status, data = transport.post_with_retries_sync(
            endpoint, body, headers, max_retries=max_retries
        )
        return success, status, data
    finally:
        duration = max(0.0, time.perf_counter() - start)
        record_http_metrics(operation, tenant, success, status, duration)


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
    """Execute an async HTTP POST with retries and metrics.
    
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
    start = time.perf_counter()
    success = False
    status = 0
    data: Any = None
    try:
        success, status, data = await transport.post_with_retries_async(
            endpoint, body, headers, max_retries=max_retries
        )
        return success, status, data
    finally:
        duration = max(0.0, time.perf_counter() - start)
        record_http_metrics(operation, tenant, success, status, duration)


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
        item_headers["X-Request-ID"] = (
            f"{headers.get('X-Request-ID', 'bulk')}:{idx}"
        )
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
        item_headers["X-Request-ID"] = (
            f"{headers.get('X-Request-ID', 'bulk')}:{idx}"
        )
        success, data = await store_http_async(transport, item, item_headers, tenant)
        results.append(data if success else None)
        if not success:
            all_success = False
    return all_success, 200 if all_success else 500, {"items": results}


__all__ = [
    "record_http_metrics",
    "http_post_with_retries_sync",
    "http_post_with_retries_async",
    "store_http_sync",
    "store_http_async",
    "store_bulk_http_sync",
    "store_bulk_http_async",
]
