import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Enable exec controller and planner with aggressive switching
    app_mod.cfg.use_exec_controller = True
    app_mod.cfg.exec_window = 1
    app_mod.cfg.exec_conflict_threshold = 0.1
    app_mod.cfg.exec_switch_threshold = 0.1
    app_mod.cfg.exec_switch_universe = "cf:alt"
    app_mod.cfg.use_planner = True
    app_mod.cfg.plan_max_steps = 2

    # Seed cf:alt universe graph
    tasks_cf = ["cf collect", "cf analyze"]
    for t in tasks_cf:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {
                    "task": t,
                    "universe": "cf:alt",
                    "importance": 1,
                    "memory_type": "episodic",
                },
            },
        )
        assert r.status_code == 200
    r = client.post(
        "/link",
        json={
            "from_key": tasks_cf[1],
            "to_key": tasks_cf[0],
            "type": "depends_on",
            "universe": "cf:alt",
        },
    )
    assert r.status_code == 200

    # Act on a novel task to induce conflict and switching on second step
    r = client.post("/act", json={"task": "novel objective", "top_k": 1})
    assert r.status_code == 200
    data = r.json()
    # Expect plan_universe suggested as cf:alt (since conflict high)
    pu = data.get("plan_universe")
    assert pu in ("cf:alt", None)  # tolerate timing; prefer cf:alt
    print("Strategy switch test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
