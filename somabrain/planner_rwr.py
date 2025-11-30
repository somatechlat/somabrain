"""
Random Walk with Restart (RWR) Planner Module.

This module provides planning capabilities using Random Walk with Restart algorithm
over the memory graph. It builds a local subgraph around a task and uses RWR to
identify the most relevant related tasks and facts based on graph connectivity.

Key Features:
- Random Walk with Restart for importance ranking
- Local subgraph construction around starting task
- Stationary probability-based node ranking
- Integration with MemoryClient for graph access
- Configurable restart probability and iteration steps

Algorithm Overview:
1. Build local neighborhood graph around starting task coordinate
2. Perform power iterations with restart to compute stationary probabilities
3. Rank nodes by their stationary probabilities (excluding start node)
4. Extract and deduplicate task/fact strings from top-ranked nodes

The RWR algorithm simulates a random walker that occasionally restarts to the
starting node, allowing it to explore the graph while maintaining connection
to the original task. This provides a balance between local and global importance.

Functions:
    rwr_plan: Main RWR-based planning function.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from common.config.settings import settings


def rwr_plan(
    task_key: str,
    mem,
    steps: Optional[int] = None,
    restart: Optional[float] = None,
    universe: Optional[str] = None,
    max_items: Optional[int] = None,
) -> List[str]:
    """
    Generate a plan using Random Walk with Restart over the local graph.

    Builds a small subgraph around the specified task and runs RWR iterations to
    identify the most important related nodes. Returns the top nodes converted
    to task/fact texts, ranked by their stationary probabilities.

    The algorithm constructs a local neighborhood graph through outward expansion,
    then uses power iteration with restart to compute node importance scores.

    Args:
        task_key (str): The key of the task to plan around. Used to find the
            starting coordinate in the memory graph.
        mem: Memory client instance for accessing graph data and retrieving payloads.
            Expected to have coord_for_key(), links_from(), and payloads_for_coords() methods.
        steps (int): Number of RWR power iterations to perform. Higher values
            provide more accurate stationary probabilities but increase computation.
            Default: 20
        restart (float): Probability of restarting to the start node at each step.
            Higher values (closer to 1.0) keep the walk more local to the start.
            Lower values allow more global exploration. Default: 0.15
        universe (Optional[str]): Optional universe identifier for multi-tenant isolation.
            If provided, restricts planning to the specified universe. Default: None
        max_items (int): Maximum number of planning items to return.
            Limits the output size. Default: 5

    Returns:
        List[str]: Ordered list of unique task/fact strings from top-ranked nodes.
            Each string represents a task or fact extracted from high-probability nodes.
            Returns empty list if insufficient graph data or single-node graph.

    Algorithm Details:
        1. Convert task_key to starting coordinate
        2. Build local neighborhood graph (max 128 nodes) via BFS expansion
        3. Initialize probability vector with 1.0 at start node
        4. Precompute row-normalized transition matrix
        5. Perform power iterations: p' = (1-r) * T * p + r * p0
        6. Rank nodes by stationary probability (excluding start)
        7. Extract and deduplicate task/fact strings from top max_items nodes

    Graph Construction:
        - Expands outward from start node following all link types
        - Limits to 32 edges per node and 128 total nodes
        - Uses link weights for transition probabilities
        - Builds adjacency matrix for efficient computation

    Note:
        This method is computationally more intensive than simple graph traversal
        but provides better ranking of semantically important nodes.
    """
    start = mem.coord_for_key(task_key, universe=universe)
    # Build a small neighborhood graph via outward expansion
    frontier: List[Tuple[float, float, float]] = [start]
    visited: Set[Tuple[float, float, float]] = set([start])
    adj: Dict[Tuple[float, float, float], Dict[Tuple[float, float, float], float]] = {}
    max_nodes = max(1, int(settings.planner_rwr_max_nodes))
    while frontier and len(visited) < max_nodes:
        u = frontier.pop(0)
        edges = mem.links_from(
            u, type_filter=None, limit=max(1, int(settings.planner_rwr_edges_per_node))
        )
        for e in edges:
            v = tuple(e.get("to"))  # type: ignore
            w = float(e.get("weight", 1.0) or 1.0)
            adj.setdefault(u, {})[v] = max(w, adj.get(u, {}).get(v, 0.0))
            if v not in visited:
                visited.add(v)
                frontier.append(v)
            if len(visited) >= max_nodes:
                break

    nodes = list(visited)
    index = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    if n <= 1:
        return []
    # Initialize probability vector p0 at start
    p = [0.0] * n
    p0 = [0.0] * n
    p[index[start]] = 1.0
    p0[index[start]] = 1.0
    # Precompute row-normalized transition matrix in sparse dict form
    T: Dict[int, Dict[int, float]] = {}
    for u, nbrs in adj.items():
        i = index[u]
        s = sum(nbrs.values()) or 1.0
        T[i] = {index[v]: w / s for v, w in nbrs.items() if v in index}
    # Power iterations with restart
    s_val = max(1, int(settings.planner_rwr_steps if steps is None else steps))
    restart_prob = float(settings.planner_rwr_restart if restart is None else restart)
    max_items_val = max(
        1, int(settings.planner_rwr_max_items if max_items is None else max_items)
    )
    for _ in range(s_val):
        newp = [0.0] * n
        for i, row in T.items():
            pi = p[i]
            if pi == 0.0:
                continue
            for j, w in row.items():
                newp[j] += (1.0 - restart_prob) * pi * w
        # restart to p0
        for i in range(n):
            newp[i] += restart_prob * p0[i]
        p = newp
    # Rank nodes (excluding start) and map to texts
    scored = [(p[i], nodes[i]) for i in range(n) if nodes[i] != start]
    scored.sort(key=lambda t: t[0], reverse=True)
    coords = [c for _, c in scored[:max_items_val]]
    items = mem.payloads_for_coords(coords, universe=universe)
    out: List[str] = []
    for it in items:
        text = str(it.get("task") or it.get("fact") or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items_val:
            break
    return out
