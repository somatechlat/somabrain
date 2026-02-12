"""Direct Memory Backend - AAAS Mode.

Implements MemoryBackend Protocol using direct SomaFractalMemory imports.
Zero HTTP latency. Requires 'aaas' extras: pip install somabrain[aaas]

AAAS = Agent As A Service mode.

This module provides a DirectMemoryBackend class that wraps SomaFractalMemory's
MemoryService and GraphService, exposing the same interface as the HTTP-based
MemoryClient. This enables sub-millisecond memory operations when SomaBrain
and SomaFractalMemory are deployed in the same process.

Usage:
    # Automatic via factory (respects SOMABRAIN_MEMORY_MODE env var)
    from somabrain.memory.backends import get_memory_backend
    backend = get_memory_backend(namespace="my_namespace")

    # Direct instantiation
    from somabrain.memory.direct_backend import DirectMemoryBackend
    backend = DirectMemoryBackend(namespace="my_namespace")

Environment:
    SOMABRAIN_MEMORY_MODE=direct  # Enable AAAS mode
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from somabrain.interfaces.memory import Coordinate

logger = logging.getLogger(__name__)

# Lazy-loaded services to avoid ImportError when not in AAAS mode
_services_cache: Dict[str, Any] = {}


def _key_to_coord(key: str) -> Coordinate:
    """Convert a string key to a deterministic 3D coordinate in [-1, 1]^3.

    Uses BLAKE2b hash for uniform distribution.

    Args:
        key: The string key to convert.

    Returns:
        A tuple of 3 floats in the range [-1, 1].
    """
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=12).digest()
    a = int.from_bytes(h[0:4], "big") / (2**32)
    b = int.from_bytes(h[4:8], "big") / (2**32)
    c = int.from_bytes(h[8:12], "big") / (2**32)
    return (2 * a - 1, 2 * b - 1, 2 * c - 1)


def _get_memory_service(namespace: str) -> Any:
    """Lazy-load SomaFractalMemory MemoryService.

    Args:
        namespace: The namespace for the memory service.

    Returns:
        MemoryService instance.

    Raises:
        ImportError: If somafractalmemory is not installed.
    """
    cache_key = f"memory:{namespace}"
    if cache_key not in _services_cache:
        try:
            from somafractalmemory.services import MemoryService
        except ImportError as e:
            raise ImportError(
                "AAAS mode requires somafractalmemory. "
                "Install with: pip install somabrain[aaas]"
            ) from e
        _services_cache[cache_key] = MemoryService(namespace=namespace)
    return _services_cache[cache_key]


def _get_graph_service(namespace: str) -> Any:
    """Lazy-load SomaFractalMemory GraphService.

    Args:
        namespace: The namespace for the graph service.

    Returns:
        GraphService instance.

    Raises:
        ImportError: If somafractalmemory is not installed.
    """
    cache_key = f"graph:{namespace}"
    if cache_key not in _services_cache:
        try:
            from somafractalmemory.services import GraphService
        except ImportError as e:
            raise ImportError(
                "AAAS mode requires somafractalmemory. "
                "Install with: pip install somabrain[aaas]"
            ) from e
        _services_cache[cache_key] = GraphService(namespace=namespace)
    return _services_cache[cache_key]


class DirectMemoryBackend:
    """Direct import backend implementing MemoryBackend Protocol.

    Use this when SomaBrain and SomaFractalMemory run in the same process.
    Provides sub-millisecond memory access by bypassing HTTP transport.

    This class implements the same interface as MemoryClient, allowing
    seamless switching between HTTP and direct modes via the factory
    function get_memory_backend().

    Attributes:
        namespace: The isolation namespace for all operations.
        tenant: The default tenant ID for operations.
    """

    def __init__(
        self,
        namespace: str = "default",
        tenant: str = "default",
    ) -> None:
        """Initialize the DirectMemoryBackend.

        Args:
            namespace: The isolation namespace for memory operations.
            tenant: The default tenant ID for multi-tenant isolation.
        """
        self.namespace = namespace
        self.tenant = tenant
        self._memory_service = _get_memory_service(namespace)
        self._graph_service = _get_graph_service(namespace)
        logger.info(
            "DirectMemoryBackend initialized",
            extra={"namespace": namespace, "tenant": tenant},
        )

    def remember(
        self,
        key: str,
        payload: dict,
        *args: Any,
        universe: Optional[str] = None,
        memory_type: str = "episodic",
        **kwargs: Any,
    ) -> Any:
        """Store memory via direct Django ORM call.

        Args:
            key: The unique key for the memory.
            payload: The data payload to store.
            universe: Optional universe/tenant override.
            memory_type: Type of memory ("episodic" or "semantic").
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            The stored Memory object.
        """
        coord = _key_to_coord(key)
        return self._memory_service.store(
            coordinate=coord,
            payload=payload,
            memory_type=memory_type,
            tenant=universe or self.tenant,
        )

    async def aremember(
        self,
        key: str,
        payload: dict,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Async wrapper for remember (runs in thread pool).

        Django ORM is synchronous, so we run in executor for async compatibility.

        Args:
            key: The unique key for the memory.
            payload: The data payload to store.
            **kwargs: Additional arguments passed to remember().

        Returns:
            The stored Memory object.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.remember(key, payload, *args, **kwargs)
        )

    def recall(
        self,
        query: str,
        *args: Any,
        top_k: int = 5,
        universe: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Any]:
        """Recall memories via direct Milvus + Postgres search.

        Args:
            query: The search query string.
            top_k: Maximum number of results to return.
            universe: Optional universe/tenant override.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            List of recalled memory payloads.
        """
        results = self._memory_service.search(
            query=query,
            top_k=top_k,
            tenant=universe or self.tenant,
        )
        # Normalize to list of payloads for MemoryBackend compatibility
        return [r.get("payload", r) if isinstance(r, dict) else r for r in results]

    async def arecall(
        self,
        query: str,
        *args: Any,
        **kwargs: Any,
    ) -> List[Any]:
        """Async wrapper for recall.

        Args:
            query: The search query string.
            **kwargs: Additional arguments passed to recall().

        Returns:
            List of recalled memory payloads.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.recall(query, *args, **kwargs)
        )

    def coord_for_key(
        self,
        key: str,
        universe: Optional[str] = None,
    ) -> Coordinate:
        """Get coordinate for a key.

        Args:
            key: The key to convert.
            universe: Ignored, for API compatibility.

        Returns:
            The 3D coordinate tuple.
        """
        return _key_to_coord(key)

    def fetch_by_coord(
        self,
        coord: Coordinate,
        universe: Optional[str] = None,
    ) -> List[Any]:
        """Fetch memory by coordinate.

        Args:
            coord: The 3D coordinate tuple.
            universe: Optional universe/tenant override.

        Returns:
            List containing the memory payload if found, empty list otherwise.
        """
        result = self._memory_service.retrieve(
            coordinate=coord,
            tenant=universe or self.tenant,
        )
        return [result] if result else []

    def delete(self, coordinate: Coordinate) -> Any:
        """Delete memory by coordinate.

        Args:
            coordinate: The 3D coordinate tuple.

        Returns:
            Result of the delete operation.
        """
        return self._memory_service.delete(
            coordinate=coordinate,
            tenant=self.tenant,
        )

    def health(self) -> dict:
        """Check backend health.

        Returns:
            Dictionary with health status.
        """
        try:
            mem_health = self._memory_service.health_check()
            graph_health = self._graph_service.health_check()
            return {
                "healthy": mem_health.get("healthy", True) and graph_health.get("healthy", True),
                "mode": "direct",
                "memory": mem_health,
                "graph": graph_health,
            }
        except Exception as e:
            logger.exception("Health check failed")
            return {"healthy": False, "mode": "direct", "error": str(e)}

    # --- Graph operations (MemoryBackend extension) ---

    def link(
        self,
        from_key: str,
        to_key: str,
        link_type: str = "related",
        weight: float = 1.0,
        **kwargs: Any,
    ) -> Any:
        """Create a graph link between two memories.

        Args:
            from_key: Source memory key.
            to_key: Target memory key.
            link_type: Type of relationship.
            weight: Link weight.
            **kwargs: Additional link data.

        Returns:
            The created GraphLink object.
        """
        from_coord = _key_to_coord(from_key)
        to_coord = _key_to_coord(to_key)
        return self._graph_service.add_link(
            from_coord=from_coord,
            to_coord=to_coord,
            link_data={"type": link_type, "weight": weight, **kwargs},
        )

    async def alink(
        self,
        from_key: str,
        to_key: str,
        **kwargs: Any,
    ) -> Any:
        """Async wrapper for link.

        Args:
            from_key: Source memory key.
            to_key: Target memory key.
            **kwargs: Additional arguments passed to link().

        Returns:
            The created GraphLink object.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.link(from_key, to_key, **kwargs)
        )

    def links_from(
        self,
        key: str,
        link_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Any]:
        """Get neighbors of a memory.

        Args:
            key: The source memory key.
            link_type: Optional filter by link type.
            limit: Maximum number of neighbors to return.

        Returns:
            List of neighbor coordinates and link data.
        """
        coord = _key_to_coord(key)
        return self._graph_service.get_neighbors(
            coord=coord,
            link_type=link_type,
            limit=limit,
            tenant=self.tenant,
        )

    def k_hop(
        self,
        key: str,
        k: int = 2,
        link_type: Optional[str] = None,
    ) -> List[Any]:
        """Get memories within k hops.

        Args:
            key: The source memory key.
            k: Number of hops.
            link_type: Optional filter by link type.

        Returns:
            List of reachable memories within k hops.
        """
        # Simple k-hop implementation using BFS
        coord = _key_to_coord(key)
        visited = set()
        visited.add(coord)
        frontier = [coord]
        results = []

        for _ in range(k):
            next_frontier = []
            for c in frontier:
                neighbors = self._graph_service.get_neighbors(
                    coord=c,
                    link_type=link_type,
                    limit=50,
                    tenant=self.tenant,
                )
                for n in neighbors:
                    n_coord = n.get("to_coordinate") or n.get("coord")
                    if n_coord and tuple(n_coord) not in visited:
                        visited.add(tuple(n_coord))
                        next_frontier.append(tuple(n_coord))
                        results.append(n)
            frontier = next_frontier

        return results

    def payloads_for_coords(
        self,
        coords: List[Coordinate],
        universe: Optional[str] = None,
    ) -> List[Any]:
        """Fetch payloads for multiple coordinates.

        Args:
            coords: List of 3D coordinate tuples.
            universe: Optional universe/tenant override.

        Returns:
            List of payloads for the given coordinates.
        """
        payloads = []
        for coord in coords:
            result = self._memory_service.retrieve(
                coordinate=coord,
                tenant=universe or self.tenant,
            )
            if result:
                payloads.append(result.get("payload", result))
        return payloads
