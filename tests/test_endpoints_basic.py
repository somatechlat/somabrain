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


def main():
    env = {
        "SOMABRAIN_USE_HRR": "false",
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT": "",
    }
    app = _fresh_app_with_env(env)
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Health
    r = client.get("/health")
    assert r.status_code == 200

    # Basic recall/remember/act
    r = client.post("/recall", json={"query": "hello", "top_k": 2})
    assert r.status_code == 200
    data = r.json()
    assert "wm" in data and "memory" in data

    payload = {"task": "write docs", "importance": 1, "memory_type": "episodic"}
    r = client.post("/remember", json={"coord": None, "payload": payload})
    assert r.status_code == 200

    r = client.post("/act", json={"task": "summarize notes", "top_k": 2})
    assert r.status_code == 200
    res = r.json()
    assert res.get("task") == "summarize notes"

    # Metrics
    m = client.get("/metrics")
    assert m.status_code == 200

    print("Basic endpoints test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
