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
    import time

    try:
        from .. import metrics as M  # lazy to avoid import cycles in tests
    except Exception as exc: raise
        M = None
    t0 = time.perf_counter()
    try:
        return bfs_plan(
            task_key,
            mem_client,
            max_steps=max_steps,
            rel_types=rel_types,
            universe=universe,
        )
    finally:
        if "t0" in locals() and M is not None:
            try:
                M.record_planning_latency("bfs", max(0.0, time.perf_counter() - t0))
            except Exception as exc: raise


def make_plan_auto(
    cfg, task_key: str, mem_client, rel_types: List[str], universe: Optional[str] = None
) -> List[str]:
    backend = str(getattr(cfg, "planner_backend", "bfs") or "bfs").lower()
    max_steps = int(getattr(cfg, "plan_max_steps", 5) or 5)
    import time

    try:
        from .. import metrics as M
    except Exception as exc: raise
        M = None
    t0 = time.perf_counter()
    try:
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
    finally:
        if "t0" in locals() and M is not None:
            try:
                M.record_planning_latency(backend, max(0.0, time.perf_counter() - t0))
            except Exception as exc: raise
