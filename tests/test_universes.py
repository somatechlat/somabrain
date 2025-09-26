import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    task = "same task"
    # Store same task in two universes
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": task,
                "universe": "real",
                "importance": 1,
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
                "task": task,
                "universe": "cf:alt",
                "importance": 1,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200

    # Link in real universe
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": "other",
                "universe": "real",
                "importance": 1,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200
    r = client.post(
        "/link",
        json={
            "from_key": task,
            "to_key": "other",
            "type": "related",
            "universe": "real",
        },
    )
    assert r.status_code == 200

    # Query links in real
    r = client.post(
        "/graph/links", json={"from_key": task, "type": "related", "universe": "real"}
    )
    assert r.status_code == 200
    edges_real = r.json().get("edges", [])
    assert len(edges_real) >= 1

    # Query links in counterfactual universe: should be empty
    r = client.post(
        "/graph/links", json={"from_key": task, "type": "related", "universe": "cf:alt"}
    )
    assert r.status_code == 200
    edges_cf = r.json().get("edges", [])
    # no links created in cf:alt so should be empty
    assert len(edges_cf) == 0
    print("Universes test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
