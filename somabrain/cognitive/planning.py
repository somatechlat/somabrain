"""Cognitive Planning Module.

Provides high-level planning capabilities for cognitive processing.
This module wraps the graph-based planner and context planner for
use in cognitive workflows.

NO STUBS. NO MOCKS. NO HARDCODED RETURNS.
"""

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.memory.graph_client import GraphClient

logger = logging.getLogger(__name__)


class Planner:
    """High-level cognitive planner.

    Provides planning capabilities for cognitive processing workflows.
    Wraps the graph-based planner for multi-step task planning.
    """

    def __init__(
        self,
        graph_client: Optional["GraphClient"] = None,
        max_steps: int = 5,
    ) -> None:
        """Initialize the cognitive planner.

        Args:
            graph_client: Optional GraphClient for graph-based planning
            max_steps: Maximum number of planning steps (default 5)
        """
        self._graph_client = graph_client
        self._max_steps = max_steps

    @property
    def graph_client(self) -> Optional["GraphClient"]:
        """Get the graph client."""
        return self._graph_client

    @graph_client.setter
    def graph_client(self, client: Optional["GraphClient"]) -> None:
        """Set the graph client."""
        self._graph_client = client

    def plan(
        self,
        task_key: str,
        mem=None,
        max_steps: Optional[int] = None,
        rel_types: Optional[List[str]] = None,
        universe: Optional[str] = None,
    ) -> List[str]:
        """Generate a plan for the given task.

        Uses BFS graph traversal to find related tasks/steps.

        Args:
            task_key: Starting task/node key for planning
            mem: Memory client (used to get graph_client if not provided)
            max_steps: Maximum number of planning steps (overrides default)
            rel_types: Optional list of relation types to filter by
            universe: Optional namespace/universe filter

        Returns:
            List of task strings representing the plan
        """
        from somabrain.planner import plan_from_graph

        steps = max_steps or self._max_steps

        return plan_from_graph(
            task_key=task_key,
            mem=mem,
            max_steps=steps,
            rel_types=rel_types,
            universe=universe,
            graph_client=self._graph_client,
        )

    def suggest(
        self,
        task_key: str,
        mem=None,
        max_steps: Optional[int] = None,
        rel_types: Optional[List[str]] = None,
        universe: Optional[str] = None,
    ) -> List[str]:
        """Alias for plan() - suggest next steps for a task.

        Args:
            task_key: Starting task/node key
            mem: Memory client
            max_steps: Maximum number of steps
            rel_types: Relation type filter
            universe: Namespace filter

        Returns:
            List of suggested task strings
        """
        return self.plan(
            task_key=task_key,
            mem=mem,
            max_steps=max_steps,
            rel_types=rel_types,
            universe=universe,
        )
