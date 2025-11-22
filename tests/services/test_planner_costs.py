import pytest

from somabrain.cognitive.planning import Planner, Step

pytestmark = [pytest.mark.unit]


def test_planner_orders_by_cost():
    planner = Planner(max_depth=3)
    ctx = {"query_text": "foo", "snapshot": {}, "planner_actions": []}
    plan = planner.plan("goal", ctx)
    # First action should be lowest cost (analyze_goal at 0.2 or communicate 0.5 if communicator present)
    assert plan, "Planner returned empty plan"
    assert plan[0].name in {"analyze_goal", "communicate", "retrieve_memory"}


def test_planner_respects_preconditions():
    planner = Planner(max_depth=2)
    ctx = {"snapshot": {}, "planner_actions": [{"name": "custom", "precondition": lambda c: False}]}
    plan = planner.plan("goal", ctx)
    assert all(step.name != "custom" for step in plan)
