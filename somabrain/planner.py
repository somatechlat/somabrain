"""
Graph-Informed Planner Module.

This module provides heuristic planning capabilities by traversing typed relations
in the memory graph around a task key. It extracts ordered lists of related tasks
and facts to create suggested plans based on semantic relationships.

Key Features:
- Graph traversal-based planning using memory relationships
- Support for multiple relation types (depends_on, causes, part_of, etc.)
- Cost-based prioritization of relationships and paths
- Bounded search to prevent excessive computation
- Integration with MemoryClient for graph access

Planning Algorithm:
1. Start from the coordinate of the given task key
2. Traverse outward following allowed relation types
3. Use cost function combining depth, relation priority, and link weights
4. Extract unique task/fact strings from visited nodes
5. Return ordered plan limited to max_steps

Relation Types (in priority order):
- depends_on: Task dependencies
- causes: Causal relationships
- part_of: Hierarchical composition
- motivates: Motivational links
- related: General associations

Functions:
    plan_from_graph: Main planning function using graph traversal.
"""

from __future__ import annotations

from typing import List

from .memory_client import MemoryClient


def plan_from_graph(
    task_key: str,
    mem: MemoryClient,
    max_steps: int = 5,
    rel_types: List[str] | None = None,
    universe: str | None = None,
) -> List[str]:
    """
    Extract a best-effort plan from typed relations around a task key.

    NOTE: Graph traversal functionality is currently unavailable. The memory
    backend API does not expose graph link endpoints (/neighbors, /link).
    This function returns an empty list until graph functionality is implemented
    in the backend service.

    Args:
        task_key (str): The key of the task to plan around.
        mem (MemoryClient): Memory client instance.
        max_steps (int): Maximum number of planning steps/tasks to return.
        rel_types (List[str] | None): List of allowed relation types to follow.
        universe (str | None): Optional universe identifier.

    Returns:
        List[str]: Empty list - graph traversal not available in current backend.
    """
    # Graph traversal requires /neighbors and /link endpoints which do not exist
    # in the current SomaFractalMemory API. Return empty list.
    return []
