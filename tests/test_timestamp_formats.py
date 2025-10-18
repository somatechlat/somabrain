import os
import sys
from importlib import import_module


def _fresh_app_with_env(env: dict):
    os.environ.update(env)
    for mod in list(sys.modules.keys()):
        if mod.startswith("somabrain"):
            sys.modules.pop(mod, None)
    app_mod = import_module("somabrain.app")
    return app_mod.app


def test_remember_accepts_iso_timestamp():
    env = {
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT": "",
        "SOMABRAIN_USE_HRR": "false",
        "SOMABRAIN_REQUIRE_MEMORY": "0",
        "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS": "0",
    }
    app = _fresh_app_with_env(env)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    iso_ts = "2025-10-03T09:30:00Z"
    task_text = "timestamp acceptance test"
    payload = {
        "task": task_text,
        "importance": 1,
        "memory_type": "episodic",
        "timestamp": iso_ts,
    }

    remember_res = client.post("/remember", json={"coord": None, "payload": payload})
    assert remember_res.status_code == 200

    recall_res = client.post("/recall", json={"query": task_text, "top_k": 5})
    assert recall_res.status_code == 200

    data = recall_res.json()
    memories = data.get("memory", [])
    # Ensure at least one memory is present and timestamps are normalized.
    assert isinstance(memories, list)
    stored = next((m for m in memories if m.get("task") == task_text), None)
    assert stored is not None
    ts_value = stored.get("timestamp")
    assert isinstance(ts_value, (int, float))

    # Links, if any, should also contain numeric timestamps.
    links = stored.get("links", []) or []
    for link in links:
        if isinstance(link, dict) and link.get("timestamp") is not None:
            assert isinstance(link["timestamp"], (int, float))
