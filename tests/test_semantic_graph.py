import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Seed two episodics
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": "rain clouds form",
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
                "task": "road gets wet",
                "importance": 2,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200

    # Link with a typed relation
    r = client.post(
        "/link",
        json={
            "from_key": "rain clouds form",
            "to_key": "road gets wet",
            "type": "causes",
        },
    )
    assert r.status_code == 200

    # Query links of type causes
    r = client.post(
        "/graph/links",
        json={"from_key": "rain clouds form", "type": "causes", "limit": 10},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("edges"), list)
    assert len(data["edges"]) >= 1
    print("Semantic graph test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
