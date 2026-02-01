"""
Shared Planning Utilities for SomaBrain.

This module provides shared utility functions used by planner.py and planner_rwr.py.
Consolidated here to reduce code duplication per VIBE coding rules.

VIBE COMPLIANT:
- Real implementations
- No stubs, no placeholders
- Shared across planning modules
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from somabrain.apps.memory.graph_client import GraphClient

logger = logging.getLogger(__name__)


def get_graph_client(mem) -> Optional["GraphClient"]:
    """
    Extract GraphClient from memory client.

    The memory client may have a graph_client attribute or we can
    construct one from its transport.

    Args:
        mem: Memory client instance

    Returns:
        GraphClient instance or None if not available
    """
    if mem is None:
        return None

    # Try direct attribute
    if hasattr(mem, "graph_client") and mem.graph_client is not None:
        return mem.graph_client

    # Try to get from _graph attribute
    if hasattr(mem, "_graph") and mem._graph is not None:
        return mem._graph

    # Try to construct from transport
    if hasattr(mem, "_transport") and mem._transport is not None:
        try:
            from somabrain.apps.memory.graph_client import GraphClient

            tenant = getattr(mem, "_tenant", "default")
            return GraphClient(mem._transport, tenant=tenant)
        except Exception as exc:
            logger.debug(
                "Could not construct GraphClient from transport", error=str(exc)
            )

    return None


def task_key_to_coord(
    task_key: str, mem, universe: Optional[str]
) -> Optional[Tuple[float, ...]]:
    """
    Convert task_key to coordinate.

    This attempts to:
    1. Parse task_key as comma-separated floats (if it's already a coord string)
    2. Look up task_key in memory to get its coordinate

    Args:
        task_key: Task key string or coordinate string
        mem: Memory client for lookup
        universe: Optional namespace filter

    Returns:
        Coordinate tuple or None if not resolvable
    """
    # Try parsing as coordinate string
    try:
        parts = task_key.split(",")
        if len(parts) >= 2:
            coord = tuple(float(p.strip()) for p in parts)
            return coord
    except (ValueError, AttributeError):
        pass

    # Try looking up in memory
    if mem is not None and hasattr(mem, "search"):
        try:
            # Search for the task_key
            results = mem.search(query=task_key, limit=1, universe=universe)
            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, "coord"):
                    return result.coord
                if hasattr(result, "coordinate"):
                    return result.coordinate
        except Exception as exc:
            logger.debug("Memory search for task_key failed", error=str(exc))

    return None


def coord_to_str(coord: Tuple[float, ...]) -> str:
    """
    Convert coordinate tuple to string for set membership.

    Args:
        coord: Coordinate tuple

    Returns:
        String representation with 6 decimal places
    """
    return ",".join(f"{c:.6f}" for c in coord)
