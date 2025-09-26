import os
import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    # Enable HRR and HRR-first re-ranking
    os.environ["SOMABRAIN_USE_HRR"] = "true"
    os.environ["SOMABRAIN_USE_HRR_FIRST"] = "true"
    os.environ["SOMABRAIN_HRR_RERANK_WEIGHT"] = "0.5"
    # Re-import app to pick up flags
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Seed WM items deliberately different
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": "alpha token",
                "importance": 2,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": "beta token",
                "importance": 2,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200

    # Query with 'alpha' and ensure recall works without error
    r = client.post("/recall", json={"query": "alpha query", "top_k": 2})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("wm"), list)
    print("HRR-first test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
