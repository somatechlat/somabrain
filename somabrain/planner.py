"""Graph-Informed Planner Module - REAL IMPLEMENTATION.

This module provides BFS graph traversal planning using the EXISTING GraphClient.
The GraphClient connects to SomaFractalMemory's /graph/neighbors endpoint.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.memory.graph_client import GraphClient, GraphNeighbor

from somabrain.metrics.planning import PLAN_GRAPH_UNAVAILABLE

logger = logging.getLogger(__name__)


def plan_from_graph(
    task_key: str,
    mem,
    max_steps: int = 5,
    rel_types: Optional[List[str]] = None,
    universe: Optional[str] = None,
    graph_client: Optional["GraphClient"] = None,
) -> List[str]:
    """
    BFS graph traversal for planning using EXISTING GraphClient.

    This function uses the fully-implemented GraphClient which connects
    to SFM's /graph/neighbors endpoint.

    Args:
        task_key: Starting task/node key for planning
        mem: Memory client (used to get graph_client if not provided)
        max_steps: Maximum number of planning steps to return
        rel_types: Optional list of relation types to filter by
        universe: Optional namespace/universe filter
        graph_client: Optional GraphClient instance (extracted from mem if not provided)

    Returns:
        List of task strings representing the plan
    """
    # Get GraphClient from memory client if not provided directly
    graph = graph_client or _get_graph_client(mem)
    if graph is None:
        PLAN_GRAPH_UNAVAILABLE.inc()
        logger.warning("GraphClient not available for planning")
        return []

    # Get starting coordinate from task_key
    start_coord = _task_key_to_coord(task_key, mem, universe)
    if start_coord is None:
        logger.debug("Could not resolve task_key to coordinate", task_key=task_key)
        return []

    # BFS traversal
    visited: set = set()
    queue: List[Tuple[Tuple[float, ...], int]] = [(start_coord, 0)]
    results: List[str] = []
    graph_limit = 20  # Limit neighbors per node

    while queue and len(results) < max_steps:
        current_coord, depth = queue.pop(0)
        coord_str = _coord_to_str(current_coord)

        if coord_str in visited:
            continue
        visited.add(coord_str)

        # Use EXISTING GraphClient.get_neighbors()
        try:
            neighbors = graph.get_neighbors(
                coord=current_coord,
                k_hop=1,
                limit=graph_limit,
                link_type=rel_types[0] if rel_types else None,
            )
        except Exception as exc:
            logger.warning("GraphClient.get_neighbors failed", error=str(exc))
            continue

        # Filter by rel_types if specified and multiple types given
        if rel_types and len(rel_types) > 1:
            neighbors = [n for n in neighbors if n.link_type in rel_types]

        # Deterministic ordering: strength desc, then coord string (Requirement 1.5)
        neighbors.sort(key=lambda n: (-n.strength, _coord_to_str(n.coord)))

        for neighbor in neighbors:
            if len(results) >= max_steps:
                break
            neighbor_str = _coord_to_str(neighbor.coord)
            if neighbor_str not in visited:
                # Extract task from metadata if available
                task_str = _extract_task_from_neighbor(neighbor)
                if task_str:
                    results.append(task_str)
                queue.append((neighbor.coord, depth + 1))

    return results


def _get_graph_client(mem) -> Optional["GraphClient"]:
    """Extract GraphClient from memory client.

    The memory client may have a graph_client attribute or we can
    construct one from its transport.
    """
    if mem is None:
        return None

    # Try direct attribute
    if hasattr(mem, "graph_client") and mem.graph_client is not None:
        return mem.graph_client

    # Try to get from _graph attribute
    if hasattr(mem, "_graph") and mem._graph is not None:
        return mem._graph

    # Try to construct from transport
    if hasattr(mem, "_transport") and mem._transport is not None:
        try:
            from somabrain.memory.graph_client import GraphClient

            tenant = getattr(mem, "_tenant", "default")
            return GraphClient(mem._transport, tenant=tenant)
        except Exception as exc:
            logger.debug("Could not construct GraphClient from transport", error=str(exc))

    return None


def _task_key_to_coord(task_key: str, mem, universe: Optional[str]) -> Optional[Tuple[float, ...]]:
    """Convert task_key to coordinate.

    This attempts to:
    1. Parse task_key as comma-separated floats (if it's already a coord string)
    2. Look up task_key in memory to get its coordinate
    """
    # Try parsing as coordinate string
    try:
        parts = task_key.split(",")
        if len(parts) >= 2:
            coord = tuple(float(p.strip()) for p in parts)
            return coord
    except (ValueError, AttributeError):
        pass

    # Try looking up in memory
    if mem is not None and hasattr(mem, "search"):
        try:
            # Search for the task_key
            results = mem.search(query=task_key, limit=1, universe=universe)
            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, "coord"):
                    return result.coord
                if hasattr(result, "coordinate"):
                    return result.coordinate
        except Exception as exc:
            logger.debug("Memory search for task_key failed", error=str(exc))

    return None


def _coord_to_str(coord: Tuple[float, ...]) -> str:
    """Convert coordinate tuple to string for set membership."""
    return ",".join(f"{c:.6f}" for c in coord)


def _extract_task_from_neighbor(neighbor: "GraphNeighbor") -> Optional[str]:
    """Extract task string from neighbor metadata."""
    if neighbor.metadata:
        # Try common metadata keys
        for key in ("task", "text", "content", "description", "name"):
            if key in neighbor.metadata and neighbor.metadata[key]:
                return str(neighbor.metadata[key])

    # Fall back to coordinate string
    return _coord_to_str(neighbor.coord)
