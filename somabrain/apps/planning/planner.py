"""Graph-Informed Planner Module - REAL IMPLEMENTATION.

This module provides BFS graph traversal planning using the EXISTING GraphClient.
The GraphClient connects to SomaFractalMemory's /graph/neighbors endpoint.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from somabrain.apps.memory.graph_client import GraphClient, GraphNeighbor

from somabrain.metrics.planning import PLAN_GRAPH_UNAVAILABLE
from somabrain.planning import coord_to_str, get_graph_client, task_key_to_coord

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
    graph = graph_client or get_graph_client(mem)
    if graph is None:
        PLAN_GRAPH_UNAVAILABLE.inc()
        logger.warning("GraphClient not available for planning")
        return []

    # Get starting coordinate from task_key
    start_coord = task_key_to_coord(task_key, mem, universe)
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
        coord_str = coord_to_str(current_coord)

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
        neighbors.sort(key=lambda n: (-n.strength, coord_to_str(n.coord)))

        for neighbor in neighbors:
            if len(results) >= max_steps:
                break
            neighbor_str = coord_to_str(neighbor.coord)
            if neighbor_str not in visited:
                # Extract task from metadata if available
                task_str = _extract_task_from_neighbor(neighbor)
                if task_str:
                    results.append(task_str)
                queue.append((neighbor.coord, depth + 1))

    return results

def _extract_task_from_neighbor(neighbor: "GraphNeighbor") -> Optional[str]:
    """Extract task string from neighbor metadata."""
    if neighbor.metadata:
        # Try common metadata keys
        for key in ("task", "text", "content", "description", "name"):
            if key in neighbor.metadata and neighbor.metadata[key]:
                return str(neighbor.metadata[key])

    # Fall back to coordinate string
    return coord_to_str(neighbor.coord)
