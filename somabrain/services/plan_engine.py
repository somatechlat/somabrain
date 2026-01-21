"""Unified Plan Engine - Single entrypoint for all planning.

This module provides PlanEngine as the single planning entrypoint,
using the REAL BFS and RWR implementations that connect to GraphClient.

NO STUBS. NO MOCKS. Uses EXISTING infrastructure.

Requirements: 6.1-6.5
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from somabrain.memory.graph_client import GraphClient

from somabrain.metrics.planning import PLAN_EMPTY, PLAN_LATENCY
from somabrain.planner import plan_from_graph
from somabrain.planner_rwr import rwr_plan

logger = logging.getLogger(__name__)


@dataclass
class PlanRequestContext:
    """Input context for planning (Requirement 6.1).

    Attributes:
        tenant_id: Tenant identifier for isolation
        task_key: Starting task/node key for planning
        task_vec: Task embedding vector
        start_coord: Starting coordinate tuple
        focus_vec: Optional focus vector for context
        time_budget_ms: Time budget in milliseconds
        max_steps: Maximum planning steps
        rel_types: Relationship types to traverse
        universe: Optional namespace/universe filter
    """

    tenant_id: str
    task_key: str
    task_vec: np.ndarray
    start_coord: tuple
    focus_vec: Optional[np.ndarray] = None
    time_budget_ms: int = 50
    max_steps: int = 5
    rel_types: List[str] = field(default_factory=list)
    universe: Optional[str] = None


@dataclass
class CompositePlan:
    """Composite plan output with multiple artifacts (Requirement 6.2).

    Attributes:
        graph_plan: Plan from graph traversal (BFS/RWR)
        context_plan: Plan from context analysis
        option_plan: Plan from option ranking
        action_plan: Plan from action sequencing
        diagnostics: Diagnostic information
        elapsed_ms: Time taken in milliseconds
    """

    graph_plan: List[str] = field(default_factory=list)
    context_plan: List[str] = field(default_factory=list)
    option_plan: List[str] = field(default_factory=list)
    action_plan: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def to_legacy_steps(self) -> List[str]:
        """Backward-compatible flat list (Requirement 6.5).

        Returns the first non-empty plan in priority order:
        graph > context > option > action
        """
        if self.graph_plan:
            return self.graph_plan
        if self.context_plan:
            return self.context_plan
        if self.option_plan:
            return self.option_plan
        return self.action_plan


class PlanEngine:
    """Single planning entrypoint using EXISTING infrastructure.

    This engine uses the REAL BFS and RWR implementations that
    connect to GraphClient for graph traversal.

    Requirements: 6.1-6.5
    """

    def __init__(
        self,
        cfg: Any,
        mem_client: Any = None,
        graph_client: Optional["GraphClient"] = None,
    ):
        """Initialize PlanEngine.

        Args:
            cfg: Configuration object with planner settings
            mem_client: Memory client for graph access
            graph_client: Optional GraphClient instance
        """
        self._cfg = cfg
        self._mem = mem_client
        self._graph = graph_client

    def plan(self, ctx: PlanRequestContext) -> CompositePlan:
        """Execute planning with time budget (Requirement 6.3).

        Args:
            ctx: Planning request context

        Returns:
            CompositePlan with results and diagnostics
        """
        t0 = time.perf_counter()
        deadline = t0 + (ctx.time_budget_ms / 1000.0)

        result = CompositePlan()
        backend = str(getattr(self._cfg, "planner_backend", "bfs") or "bfs").lower()

        try:
            # Check time budget (Requirement 6.3)
            if time.perf_counter() >= deadline:
                result.diagnostics["timeout"] = True
                result.diagnostics["reason"] = "timeout_before_start"
            else:
                # Execute planning based on backend
                if backend == "rwr":
                    result.graph_plan = self._execute_rwr(ctx)
                else:
                    result.graph_plan = self._execute_bfs(ctx)

        except Exception as exc:
            # Fail-soft: continue with empty plan (Requirement 6.4)
            logger.warning(f"Planning failed: {exc}")
            result.diagnostics["error"] = str(exc)
            result.diagnostics["reason"] = "exception"

        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        PLAN_LATENCY.labels(backend=backend).observe(result.elapsed_ms / 1000)

        # Record empty plan metric
        if not result.to_legacy_steps():
            reason = result.diagnostics.get("reason", "empty_graph")
            PLAN_EMPTY.labels(reason=reason).inc()

        return result

    def _execute_bfs(self, ctx: PlanRequestContext) -> List[str]:
        """Execute BFS planning using REAL implementation."""
        return plan_from_graph(
            task_key=ctx.task_key,
            mem=self._mem,
            max_steps=ctx.max_steps,
            rel_types=ctx.rel_types if ctx.rel_types else None,
            universe=ctx.universe,
            graph_client=self._graph,
        )

    def _execute_rwr(self, ctx: PlanRequestContext) -> List[str]:
        """Execute RWR planning using REAL implementation."""
        return rwr_plan(
            task_key=ctx.task_key,
            mem=self._mem,
            steps=int(getattr(self._cfg, "planner_rwr_steps", 20) or 20),
            restart=float(getattr(self._cfg, "planner_rwr_restart", 0.15) or 0.15),
            universe=ctx.universe,
            max_items=ctx.max_steps,
            graph_client=self._graph,
        )
