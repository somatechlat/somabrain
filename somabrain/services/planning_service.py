"""Planning Service for SomaBrain.

This module provides planning functions that generate action sequences
using graph-based algorithms (BFS or Random Walk with Restart).

VIBE Compliance:
    - Uses metrics interface directly (no lazy imports for circular avoidance)
    - record_planning_latency imported from metrics.predictor (no circular deps)
    - All metrics calls are best-effort (silent failure on metrics errors)
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from ..metrics.predictor import record_planning_latency
from ..planner import plan_from_graph as _bfs, plan_from_graph as bfs_plan
from ..planner_rwr import rwr_plan as _rwr

logger = logging.getLogger(__name__)


def make_plan(
    task_key: str,
    mem_client,
    max_steps: int,
    rel_types: List[str],
    universe: Optional[str] = None,
) -> List[str]:
    """Generate a plan using BFS graph traversal.

    Args:
        task_key: Starting task/node key for planning
        mem_client: Memory client for graph access
        max_steps: Maximum number of steps in the plan
        rel_types: Relationship types to traverse
        universe: Optional namespace/universe filter

    Returns:
        List of task keys representing the plan
    """
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
        latency = max(0.0, time.perf_counter() - t0)
        try:
            record_planning_latency("bfs", latency)
        except Exception as exc:
            logger.debug("Failed to record planning latency metric", exc_info=exc)


def make_plan_auto(
    cfg, task_key: str, mem_client, rel_types: List[str], universe: Optional[str] = None
) -> List[str]:
    """Generate a plan using configured backend (BFS or RWR).

    Args:
        cfg: Configuration object with planner settings
        task_key: Starting task/node key for planning
        mem_client: Memory client for graph access
        rel_types: Relationship types to traverse
        universe: Optional namespace/universe filter

    Returns:
        List of task keys representing the plan
    """
    backend = str(getattr(cfg, "planner_backend", "bfs") or "bfs").lower()
    max_steps = int(getattr(cfg, "plan_max_steps", 5) or 5)
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
        latency = max(0.0, time.perf_counter() - t0)
        try:
            record_planning_latency(backend, latency)
        except Exception as exc:
            logger.debug("Failed to record planning latency metric", exc_info=exc)
