import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app

    # configure clustering to be lenient for test
    app_mod.cfg.reflect_similarity_threshold = 0.2
    app_mod.cfg.reflect_min_cluster_size = 2
    app_mod.cfg.reflect_max_summaries = 3

    client = TestClient(app)

    # Seed episodics in two themes
    for task in [
        "write docs for API",
        "update documentation readme",
        "improve docs examples",
        "fix unit tests",
        "add integration tests",
        "refactor test helpers",
    ]:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": task, "importance": 1, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    # Run reflection
    r = client.post("/reflect")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("created", 0) >= 1
    assert isinstance(data.get("summaries", []), list)
    print("Reflection v2 test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
