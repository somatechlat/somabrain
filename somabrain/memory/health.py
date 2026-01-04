"""Memory service health check functionality.

Extracted from memory_client.py per monolithic-decomposition spec.
Provides health check and degradation detection for the memory service.

Per Requirements E3.1-E3.5:
- E3.1: Returns structured component status (kv_store, vector_store, graph_store)
- E3.2: Reports degraded (not failed) when any component unhealthy
- E3.3: Lists specific unhealthy components
- E3.4: Uses 2-second timeout for health check
- E3.5: Determines degraded status and lists unhealthy components
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def check_memory_health(
    transport: Optional["MemoryHTTPTransport"],
    response_json_fn: callable,
) -> Dict[str, Any]:
    """Return health information from the external memory service.

    Per Requirements E3.1-E3.5:
    - Returns structured component status (kv_store, vector_store, graph_store)
    - Reports degraded (not failed) when any component unhealthy
    - Lists specific unhealthy components
    - Users 5-second timeout for health check

    Args:
        transport: HTTP transport for SFM communication.
        response_json_fn: Function to parse JSON response.

    Returns:
        Health status dictionary with component statuses.
    """
    if transport is None or transport.client is None:
        return {
            "healthy": False,
            "error": "HTTP client not configured",
            "degraded": True,
            "degraded_components": ["http_client"],
            "kv_store": False,
            "vector_store": False,
            "graph_store": False,
        }

    try:
        # E3.4: 5-second timeout for health check
        r = transport.client.get("/health", timeout=5.0)
        status_code = int(getattr(r, "status_code", 0) or 0)

        if status_code != 200:
            return {
                "healthy": False,
                "status": status_code,
                "degraded": True,
                "degraded_components": ["sfm_api"],
                "kv_store": False,
                "vector_store": False,
                "graph_store": False,
            }

        data = response_json_fn(r) or {}
        if not isinstance(data, dict):
            return {
                "healthy": False,
                "error": "unexpected health payload",
                "degraded": True,
                "degraded_components": ["sfm_response"],
                "kv_store": False,
                "vector_store": False,
                "graph_store": False,
            }

        # E3.1: Extract component status (Compatible with new Services List schema)
        if "services" in data and isinstance(data["services"], list):
            services_map = {s["name"]: s["healthy"] for s in data["services"]}
            kv = services_map.get("redis", False)
            vec = services_map.get("milvus", False)
            graph = services_map.get("postgresql", False)
        else:
            # Fallback to backend schema if flattened
            kv = bool(data.get("kv_store"))
            vec = bool(data.get("vector_store"))
            graph = bool(data.get("graph_store"))

        # E3.2, E3.5: Determine degraded status and list unhealthy components
        degraded_components = []
        if not kv:
            degraded_components.append("kv_store")
        if not vec:
            degraded_components.append("vector_store")
        if not graph:
            degraded_components.append("graph_store")

        is_degraded = len(degraded_components) > 0
        is_healthy = kv and vec and graph

        return {
            **data,
            "healthy": is_healthy,
            "kv_store": kv,
            "vector_store": vec,
            "graph_store": graph,
            "degraded": is_degraded,
            "degraded_components": degraded_components,
        }

    except Exception as exc:
        # E3.3: SFM unreachable - report degraded with sfm_unreachable
        return {
            "healthy": False,
            "error": str(exc),
            "degraded": True,
            "degraded_components": ["sfm_unreachable"],
            "kv_store": False,
            "vector_store": False,
            "graph_store": False,
        }


def require_healthy(health_fn: callable) -> None:
    """Raise error if memory service is not fully healthy.

    Args:
        health_fn: Function that returns health status dictionary.

    Raises:
        RuntimeError: If memory service is not fully healthy.
    """
    health = health_fn()
    if not health.get("healthy"):
        missing = [
            c for c in ("kv_store", "vector_store", "graph_store") if not health.get(c)
        ]
        raise RuntimeError(
            f"Memory service unavailable: {', '.join(missing) or 'unknown'}"
        )
