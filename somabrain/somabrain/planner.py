from __future__ import annotations

from collections import deque
from typing import List, Tuple, Set, Dict

from .memory_client import MemoryClient


def plan_from_graph(task_key: str, mem: MemoryClient, max_steps: int = 5, rel_types: List[str] | None = None, universe: str | None = None) -> List[str]:
    """Best-effort plan derived from typed relations around task_key.

    Traverses outward following allowed relation types and returns a list of
    unique task/fact strings as a suggested plan. This is heuristic and bounded.
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
    coords_sorted = sorted([c for c in coords if c in best_cost], key=lambda c: best_cost[c])
    for p in mem.payloads_for_coords(coords_sorted, universe=universe):
        text = str(p.get("task") or p.get("fact") or "").strip()
        if text and text not in plan:
            plan.append(text)
            if len(plan) >= max_steps:
                break
    return plan
