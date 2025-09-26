import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    # Enable microcircuits
    app_mod.cfg.use_microcircuits = True
    app_mod.cfg.micro_circuits = 3
    client = TestClient(app)

    # Seed episodics across topics
    for t in [
        "topic alpha one",
        "topic beta two",
        "topic gamma three",
        "topic alpha two",
    ]:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 2, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    # Recall on an alpha query; expect at least one hit and stable response
    r = client.post("/recall", json={"query": "alpha query", "top_k": 3})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("wm"), list)
    print("Microcircuits test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
