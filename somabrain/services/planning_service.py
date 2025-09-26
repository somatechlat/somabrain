from __future__ import annotations

from typing import List, Optional

from ..planner import plan_from_graph as _bfs, plan_from_graph as bfs_plan
from ..planner_rwr import rwr_plan as _rwr


def make_plan(
    task_key: str,
    mem_client,
    max_steps: int,
    rel_types: List[str],
    universe: Optional[str] = None,
) -> List[str]:
    return bfs_plan(
        task_key,
        mem_client,
        max_steps=max_steps,
        rel_types=rel_types,
        universe=universe,
    )


def make_plan_auto(
    cfg, task_key: str, mem_client, rel_types: List[str], universe: Optional[str] = None
) -> List[str]:
    backend = str(getattr(cfg, "planner_backend", "bfs") or "bfs").lower()
    max_steps = int(getattr(cfg, "plan_max_steps", 5) or 5)
    if backend == "rwr":
        return _rwr(
            task_key,
            mem_client,
            steps=int(getattr(cfg, "rwr_steps", 20) or 20),
            restart=float(getattr(cfg, "rwr_restart", 0.15) or 0.15),
            universe=universe,
            max_items=max_steps,
        )
    return _bfs(
        task_key,
        mem_client,
        max_steps=max_steps,
        rel_types=rel_types,
        universe=universe,
    )
