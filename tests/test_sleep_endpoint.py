import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # seed some episodics
    for t in ["sleep a", "sleep b", "sleep c"]:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 2, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    r = client.post("/sleep/run", json={"nrem": True, "rem": True})
    assert r.status_code == 200
    data = r.json()
    assert "nrem" in data and "rem" in data
    print("Sleep endpoint test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
