from __future__ import annotations

from typing import List, Tuple, Dict, Optional, Set


def rwr_plan(task_key: str, mem, steps: int = 20, restart: float = 0.15, universe: Optional[str] = None, max_items: int = 5) -> List[str]:
    """Random Walk with Restart (RWR) over the local graph view.

    Builds a small subgraph around the start and runs a few RWR iterations. Returns
    the top nodes (by stationary probability) converted to task/fact texts.
    """
    start = mem.coord_for_key(task_key, universe=universe)
    # Build a small neighborhood graph via outward expansion
    frontier: List[Tuple[float, float, float]] = [start]
    visited: Set[Tuple[float, float, float]] = set([start])
    adj: Dict[Tuple[float, float, float], Dict[Tuple[float, float, float], float]] = {}
    max_nodes = 128
    while frontier and len(visited) < max_nodes:
        u = frontier.pop(0)
        edges = mem.links_from(u, type_filter=None, limit=32)
        for e in edges:
            v = tuple(e.get('to'))  # type: ignore
            w = float(e.get('weight', 1.0) or 1.0)
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
    for _ in range(max(1, int(steps))):
        newp = [0.0] * n
        for i, row in T.items():
            pi = p[i]
            if pi == 0.0:
                continue
            for j, w in row.items():
                newp[j] += (1.0 - restart) * pi * w
        # restart to p0
        for i in range(n):
            newp[i] += restart * p0[i]
        p = newp
    # Rank nodes (excluding start) and map to texts
    scored = [(p[i], nodes[i]) for i in range(n) if nodes[i] != start]
    scored.sort(key=lambda t: t[0], reverse=True)
    coords = [c for _, c in scored[:max_items]]
    items = mem.payloads_for_coords(coords, universe=universe)
    out: List[str] = []
    for it in items:
        text = str(it.get('task') or it.get('fact') or '').strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out

