import pytest

from somabrain.cognitive.planning import Planner, Step

pytestmark = [pytest.mark.unit]


def test_execute_stops_on_failure():
    planner = Planner(max_depth=2)
    plan = [Step("a"), Step("b")]

    calls = []

    def exec_fn(step: Step) -> bool:
        calls.append(step.name)
        return step.name != "b"

    results = planner.execute(plan, exec_fn)
    assert calls == ["a", "b"]
    assert results[-1]["ok"] is False

