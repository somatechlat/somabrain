import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Baseline /act on task A
    r = client.post("/act", json={"task": "analyze data A", "top_k": 1})
    assert r.status_code == 200
    base = r.json()["results"][0]["salience"]

    # Set personality with high curiosity and risk tolerance
    r = client.post(
        "/personality", json={"traits": {"curiosity": 1.0, "risk_tolerance": 1.0}}
    )
    assert r.status_code == 200

    # /act on a different fresh task B; expect salience to be >= baseline due to
    # ACh and lower thresholds
    r = client.post("/act", json={"task": "analyze data B", "top_k": 1})
    assert r.status_code == 200
    sal2 = r.json()["results"][0]["salience"]
    assert sal2 >= base
    print("Personality test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
