"""Category C2: Planning and Decision Making Tests.

**Feature: full-capacity-testing**
**Validates: Requirements C2.1, C2.2, C2.3, C2.4, C2.5**

Tests that verify the real graph-based planner in ``somabrain.admin.cognitive.planning``.
The planner uses BFS over SomaFractalMemory graph neighbors; without a live memory
backend it degrades gracefully to an empty plan. These tests exercise the public
API against real code and only gate the graph-dependent paths on memory availability.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import pytest

from somabrain.admin.cognitive.planning import Planner


def _sfm_available() -> bool:
    """Return True if the SomaFractalMemory HTTP API appears reachable."""
    import urllib.request

    url = os.environ.get("SOMABRAIN_MEMORY_URL", "http://localhost:10101")
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.cognitive_proof
class TestPlanningAndDecisionMaking:
    """Tests for planning and decision making.

    **Feature: full-capacity-testing, Category C2: Planning**
    **Validates: Requirements C2.1, C2.2, C2.3, C2.4, C2.5**
    """

    def test_planner_initializes_with_defaults(self) -> None:
        """C2.1: Planner initializes with sensible defaults."""
        planner = Planner()
        assert planner._max_steps == 5
        assert planner._graph_client is None

    def test_planner_plan_returns_empty_without_memory_client(self) -> None:
        """C2.1: Planning without a memory client returns an empty plan."""
        planner = Planner(max_steps=3)
        plan = planner.plan("analyze_goal")
        assert plan == []

    def test_planner_suggest_is_alias_for_plan(self) -> None:
        """C2.2: ``suggest`` delegates to ``plan`` and returns a list."""
        planner = Planner(max_steps=3)
        plan = planner.suggest("1.0,2.0")
        assert isinstance(plan, list)

    def test_planner_respects_max_steps(self) -> None:
        """C2.3: Planner accepts and stores a custom step limit."""
        planner = Planner(max_steps=7)
        assert planner._max_steps == 7

    def test_task_key_parsed_as_coordinate(self) -> None:
        """C2.4: A coordinate task key is parsed but plan stays empty without graph."""
        planner = Planner(max_steps=3)
        plan = planner.plan("1.5,2.5,3.5")
        assert isinstance(plan, list)


@pytest.mark.cognitive_proof
@pytest.mark.skipif(not _sfm_available(), reason="SomaFractalMemory not reachable")
class TestPlanningWithLiveMemory:
    """Graph-dependent planning tests requiring a live SomaFractalMemory backend."""

    def test_plan_returns_list_of_strings(self) -> None:
        """C2.5: Planning with a real graph client returns string task steps."""
        from somabrain.memory.client import MemoryClient

        transport: Dict[str, Any] = {
            "base_url": os.environ.get("SOMABRAIN_MEMORY_URL", "http://localhost:10101"),
            "token": os.environ.get("SOMABRAIN_MEMORY_HTTP_TOKEN", ""),
        }
        client = MemoryClient(transport, tenant="default")
        planner = Planner(graph_client=client, max_steps=3)

        plan = planner.plan("analyze_goal", universe="test")

        assert isinstance(plan, list)
        assert all(isinstance(step, str) for step in plan)
