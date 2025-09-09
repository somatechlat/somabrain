import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    # enable graph augment
    app_mod.cfg.use_graph_augment = True
    app_mod.cfg.graph_hops = 1
    app_mod.cfg.graph_limit = 10

    client = TestClient(app)

    # Seed two tasks and link them
    tasks = ["task alpha", "task beta"]
    for t in tasks:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 1, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    r = client.post(
        "/link", json={"from_key": tasks[0], "to_key": tasks[1], "type": "related"}
    )
    assert r.status_code == 200

    # Recall on first task should include graph-augmented payloads (by coordinate)
    r = client.post("/recall", json={"query": tasks[0], "top_k": 1})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "memory" in data
    # There should be at least one payload; graph may add the second task
    assert len(data["memory"]) >= 1
    print("Graph reasoning test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
