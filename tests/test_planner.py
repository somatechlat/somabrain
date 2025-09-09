import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    # enable planner via config
    app_mod.cfg.use_planner = True
    app_mod.cfg.plan_max_steps = 3
    client = TestClient(app)

    # Seed tasks and links forming a tiny plan graph
    tasks = ["collect data", "analyze data", "report results"]
    for t in tasks:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 2, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200
    # Links: collect -> analyze (depends_on), analyze -> report (causes)
    r = client.post(
        "/link", json={"from_key": tasks[1], "to_key": tasks[0], "type": "depends_on"}
    )
    assert r.status_code == 200
    r = client.post(
        "/link", json={"from_key": tasks[1], "to_key": tasks[2], "type": "causes"}
    )
    assert r.status_code == 200

    # Act on analyze task and expect a plan containing neighbors
    r = client.post("/act", json={"task": tasks[1], "top_k": 2})
    assert r.status_code == 200
    data = r.json()
    plan = data.get("plan", []) or []
    assert any("collect data" in s for s in plan) or any(
        "report results" in s for s in plan
    )
    print("Planner test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
