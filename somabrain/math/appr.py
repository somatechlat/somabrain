"""Approximate Personalized PageRank (APPR) push algorithm.

Provides a simple, memory-efficient implementation of APPR used for local
graph diffusion and seed-set expansion. This is a small deterministic push-based
algorithm suitable for unit tests and small graphs.
"""

from typing import Dict, Iterable, Optional, Tuple

# lazy import of runtime config to avoid circular imports
# Unified configuration – use central Settings instance
from django.conf import settings


def appr_push(
    adj: Dict[int, Iterable[Tuple[int, float]]],
    seed: int,
    alpha: float = 0.85,
    eps: Optional[float] = None,
) -> Dict[int, float]:
    """Compute APPR vector for a single seed node.

    adj: adjacency list mapping node -> iterable of (neighbor, weight)
    seed: seed node id
    alpha: teleport/probability
    eps: residual threshold for push
    Returns: dictionary node -> approximate PPR score
    """
    # Use dictionaries for sparse vectors
    # resolve eps from truth-budget if not provided
    if eps is None:
        eps = getattr(settings, "truth_appr_eps", 1e-4)

    r = {seed: 1.0}
    p = {}
    while r:
        # find a node with large residual
        u, ru = next(((u, ru) for u, ru in r.items() if ru > eps), (None, None))
        if u is None:
            break
        # push from u
        push = ru
        p[u] = p.get(u, 0.0) + alpha * push
        remain = (1 - alpha) * push
        # distribute remain to neighbors
        neighbors = list(adj.get(u, []))
        if neighbors:
            total_w = sum(w for _, w in neighbors)
            for v, w in neighbors:
                add = remain * (w / total_w if total_w > 0 else 0.0)
                r[v] = r.get(v, 0.0) + add
        # remove residual at u
        del r[u]
    return p
