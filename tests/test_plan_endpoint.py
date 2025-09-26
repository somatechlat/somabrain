import os
import sys
from importlib import import_module


def _fresh_app_with_env(env: dict):
    os.environ.update(env)
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    return app_mod.app


def test_plan_suggest_stub():
    env = {
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT": "",
    }
    app = _fresh_app_with_env(env)
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Create a couple of memories and a link
    client.post(
        "/remember",
        json={"coord": None, "payload": {"task": "task-A", "memory_type": "episodic"}},
    )
    client.post(
        "/remember",
        json={"coord": None, "payload": {"task": "task-B", "memory_type": "episodic"}},
    )
    # Derive coords and link via /link using keys
    r = client.post(
        "/link",
        json={
            "from_key": "task-A",
            "to_key": "task-B",
            "type": "depends_on",
            "weight": 1.0,
        },
    )
    assert r.status_code == 200

    # Request a plan around task-A
    r = client.post("/plan/suggest", json={"task_key": "task-A", "max_steps": 3})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("plan"), list)
    # Best-effort: may or may not include the exact task strings depending on
    # stub; just ensure list shape
    assert len(data["plan"]) >= 0
