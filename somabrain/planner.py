from __future__ import annotations
from collections import deque
from typing import Dict, List, Set, Tuple
from .memory_client import MemoryClient

"""
Graph-Informed Planner Module.

This module provides heuristic planning capabilities by traversing typed relations
in the memory graph around a task key. It extracts ordered lists of related tasks
and facts to create suggested plans based on semantic relationships.

Key Features:
    pass
- Graph traversal-based planning using memory relationships
- Support for multiple relation types (depends_on, causes, part_of, etc.)
- Cost-based prioritization of relationships and paths
- Bounded search to prevent excessive computation
- Integration with MemoryClient for graph access

Planning Algorithm:
    pass
1. Start from the coordinate of the given task key
2. Traverse outward following allowed relation types
3. Use cost function combining depth, relation priority, and link weights
4. Extract unique task/fact strings from visited nodes
5. Return ordered plan limited to max_steps

Relation Types (in priority order):
    pass
- depends_on: Task dependencies
- causes: Causal relationships
- part_of: Hierarchical composition
- motivates: Motivational links
- related: General associations

Functions:
    plan_from_graph: Main planning function using graph traversal.
"""





def plan_from_graph(
    task_key: str,
    mem: MemoryClient,
    max_steps: int = 5,
    rel_types: List[str] | None = None,
    universe: str | None = None, ) -> List[str]:
        pass
    """
    Extract a best-effort plan from typed relations around a task key.

    Performs heuristic planning by traversing the memory graph outward from the
    specified task key, following relationships of allowed types. Returns an
    ordered list of unique task/fact strings as a suggested plan.

    The algorithm uses a cost-based approach to prioritize more relevant relationships
    and bounds the search to prevent excessive computation.

    Args:
        task_key (str): The key of the task to plan around. Used to find the
            starting coordinate in the memory graph.
        mem (MemoryClient): Memory client instance for accessing graph data
            and retrieving payloads.
        max_steps (int): Maximum number of planning steps/tasks to return.
            Limits the plan length to prevent overly complex plans. Default: 5
        rel_types (List[str] | None): List of allowed relation types to follow.
            If None, uses default types: ["depends_on", "causes", "part_of", "motivates", "related"]
        universe (str | None): Optional universe identifier for multi-tenant isolation.
            If provided, restricts planning to the specified universe.

    Returns:
        List[str]: Ordered list of unique task/fact strings forming the plan.
            Each string represents a task or fact extracted from visited graph nodes.
            Returns empty list if no related content is found.

    Algorithm Details:
        1. Convert task_key to starting coordinate using mem.coord_for_key()
        2. Perform BFS traversal with cost-based prioritization
        3. Cost function: depth + relation_priority + (1/link_weight)
        4. Extract payloads from visited coordinates (excluding start)
        5. Sort by cost and deduplicate task/fact strings
        6. Return up to max_steps items

    Relation Priority:
        Relations are prioritized in the order they appear in rel_types.
        Lower priority values are preferred in the cost function.

    Note:
        This is a heuristic approach that may not find optimal plans but provides
        reasonable suggestions based on semantic relationships in memory.
    """
    rel_types = rel_types or ["depends_on", "causes", "part_of", "motivates", "related"]
    # Relation type priority weights (lower is preferred)
    rel_weight: Dict[str, float] = {t: float(i) for i, t in enumerate(rel_types)}
    start = mem.coord_for_key(task_key, universe=universe)
    visited: Set[Tuple[float, float, float]] = set([start])
    queue: deque[Tuple[Tuple[float, float, float], int]] = deque([(start, 0)])
    plan: List[str] = []
    best_cost: Dict[Tuple[float, float, float], float] = {}
    while queue and len(plan) < max_steps:
        u, d = queue.popleft()
        # neighbors filtered by types; iterate types for determinism
        for t in rel_types:
            edges = mem.links_from(u, type_filter=t, limit=16)
            for e in edges:
                v = tuple(e["to"])  # type: ignore
                # compute a cost combining depth, relation priority, and inverse link weight
                w = float(e.get("weight", 1.0) or 1.0)
                inv_w = 1.0 / max(1e-6, w)
                cost = float(d + 1) + rel_weight.get(t, 10.0) + inv_w
                if v not in best_cost or cost < best_cost[v]:
                    best_cost[v] = cost
                if v not in visited:
                    visited.add(v)
                    queue.append((v, d + 1))
    # Convert visited coords (excluding start) to payload texts
    coords = [c for c in visited if c != start]
    # Sort visited coords by best_cost and map to unique texts
    coords_sorted = sorted(
        [c for c in coords if c in best_cost], key=lambda c: best_cost[c]
    )
    for p in mem.payloads_for_coords(coords_sorted, universe=universe):
        text = str(p.get("task") or p.get("fact") or "").strip()
        if text and text not in plan:
            plan.append(text)
            if len(plan) >= max_steps:
                break
    return plan
