import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Get baseline
    r = client.get("/neuromodulators")
    assert r.status_code == 200
    base = r.json()
    assert set(base.keys()) == {
        "dopamine",
        "serotonin",
        "noradrenaline",
        "acetylcholine",
    }

    # Set new values (some out of range to test clamping)
    r = client.post(
        "/neuromodulators",
        json={
            "dopamine": 1.0,
            "serotonin": 0.9,
            "noradrenaline": 0.2,
            "acetylcholine": 0.05,
        },
    )
    assert r.status_code == 200
    nm = r.json()
    assert 0.2 <= nm["dopamine"] <= 0.8
    assert 0.0 <= nm["noradrenaline"] <= 0.1
    # Read back
    r = client.get("/neuromodulators")
    assert r.status_code == 200
    print("Neuromodulators test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
