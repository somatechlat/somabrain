"""Random Walk with Restart (RWR) Planner Module - REAL IMPLEMENTATION.

This module provides RWR-based planning using the EXISTING GraphClient.
The GraphClient connects to SomaFractalMemory's /graph/neighbors endpoint.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from somabrain.memory.graph_client import GraphClient

from somabrain.metrics.planning import PLAN_GRAPH_UNAVAILABLE

logger = logging.getLogger(__name__)


def rwr_plan(
    task_key: str,
    mem,
    steps: Optional[int] = None,
    restart: Optional[float] = None,
    universe: Optional[str] = None,
    max_items: Optional[int] = None,
    graph_client: Optional["GraphClient"] = None,
) -> List[str]:
    """
    Random Walk with Restart planning using EXISTING GraphClient.

    This function uses the fully-implemented GraphClient which connects
    to SFM's /graph/neighbors endpoint.

    Args:
        task_key: Starting task/node key for planning
        mem: Memory client (used to get graph_client if not provided)
        steps: Number of RWR power iterations (default: 20)
        restart: Restart probability (default: 0.15)
        universe: Optional namespace/universe filter
        max_items: Maximum items to return (default: 5)
        graph_client: Optional GraphClient instance

    Returns:
        List of task strings representing the plan, ranked by RWR probability
    """
    # Default parameters
    steps = steps if steps is not None else 20
    restart = restart if restart is not None else 0.15
    max_items = max_items if max_items is not None else 5
    max_nodes = 100  # Maximum nodes in local subgraph

    # Get GraphClient from memory client if not provided directly
    graph = graph_client or _get_graph_client(mem)
    if graph is None:
        PLAN_GRAPH_UNAVAILABLE.inc()
        logger.warning("GraphClient not available for RWR planning")
        return []

    # Get starting coordinate from task_key
    start_coord = _task_key_to_coord(task_key, mem, universe)
    if start_coord is None:
        logger.debug("Could not resolve task_key to coordinate", task_key=task_key)
        return []

    # Build local subgraph using GraphClient.get_neighbors()
    nodes, edges = _build_local_subgraph(graph, start_coord, max_nodes)

    if len(nodes) < 2:
        logger.debug("Subgraph too small for RWR", node_count=len(nodes))
        return []

    # Initialize probability vector
    n = len(nodes)
    node_list = list(nodes.keys())

    start_str = _coord_to_str(start_coord)
    if start_str not in nodes:
        logger.debug("Start node not in subgraph")
        return []

    start_idx = node_list.index(start_str)

    p = np.zeros(n, dtype=np.float64)
    p[start_idx] = 1.0

    # Build transition matrix
    T = _build_transition_matrix(nodes, edges, node_list)

    # Power iteration with restart (Requirement 2.2, 2.3)
    for _ in range(steps):
        p_new = (1 - restart) * (T @ p)
        p_new[start_idx] += restart
        total = np.sum(p_new)
        if total > 1e-12:
            p = p_new / total
        else:
            p = p_new

    # Rank nodes by probability (exclude start)
    # Deterministic tie-breaking: sort by probability desc, then coord string (Requirement 2.4)
    ranked = sorted(
        [(i, p[i]) for i in range(n) if i != start_idx],
        key=lambda x: (-x[1], node_list[x[0]]),
    )

    # Extract task strings
    results: List[str] = []
    for idx, prob in ranked[:max_items]:
        coord_str = node_list[idx]
        node_data = nodes[coord_str]
        task_str = node_data.get("task") or node_data.get("text") or coord_str
        results.append(task_str)

    return results


def _build_local_subgraph(
    graph: "GraphClient",
    start_coord: Tuple[float, ...],
    max_nodes: int,
) -> Tuple[Dict[str, Dict], List[Tuple[str, str, float]]]:
    """Build local subgraph using GraphClient.get_neighbors().

    Returns:
        Tuple of (nodes dict, edges list)
        - nodes: {coord_str: {coord, task, ...}}
        - edges: [(from_str, to_str, strength), ...]
    """
    nodes: Dict[str, Dict] = {}
    edges: List[Tuple[str, str, float]] = []
    queue = [start_coord]

    while queue and len(nodes) < max_nodes:
        coord = queue.pop(0)
        coord_str = _coord_to_str(coord)

        if coord_str in nodes:
            continue

        nodes[coord_str] = {"coord": coord}

        # Use EXISTING GraphClient.get_neighbors()
        try:
            neighbors = graph.get_neighbors(coord, k_hop=1, limit=20)
        except Exception as exc:
            logger.debug("get_neighbors failed in subgraph build", error=str(exc))
            continue

        for neighbor in neighbors:
            neighbor_str = _coord_to_str(neighbor.coord)
            edges.append((coord_str, neighbor_str, neighbor.strength))

            # Store metadata if available
            if neighbor_str not in nodes:
                node_data = {"coord": neighbor.coord}
                if neighbor.metadata:
                    node_data.update(neighbor.metadata)
                nodes[neighbor_str] = node_data

            if neighbor_str not in nodes and len(nodes) < max_nodes:
                queue.append(neighbor.coord)

    return nodes, edges


def _build_transition_matrix(
    nodes: Dict[str, Dict],
    edges: List[Tuple[str, str, float]],
    node_list: List[str],
) -> np.ndarray:
    """Build row-stochastic transition matrix for RWR.

    The matrix T is column-stochastic: T[j,i] = probability of going from i to j.
    """
    n = len(node_list)
    node_idx = {node: i for i, node in enumerate(node_list)}
    T = np.zeros((n, n), dtype=np.float64)

    for from_node, to_node, strength in edges:
        if from_node in node_idx and to_node in node_idx:
            # Edge from from_node to to_node with given strength
            T[node_idx[to_node], node_idx[from_node]] = strength

    # Normalize columns to make column-stochastic
    col_sums = T.sum(axis=0)
    # Avoid division by zero
    col_sums[col_sums == 0] = 1.0
    T = T / col_sums

    return T


def _get_graph_client(mem) -> Optional["GraphClient"]:
    """Extract GraphClient from memory client."""
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
            logger.debug("Could not construct GraphClient", error=str(exc))

    return None


def _task_key_to_coord(
    task_key: str, mem, universe: Optional[str]
) -> Optional[Tuple[float, ...]]:
    """Convert task_key to coordinate."""
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
    """Convert coordinate tuple to string."""
    return ",".join(f"{c:.6f}" for c in coord)
