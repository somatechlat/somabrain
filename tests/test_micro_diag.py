import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    app_mod.cfg.use_microcircuits = True
    app_mod.cfg.micro_circuits = 2
    client = TestClient(app)

    # Seed items, then call diagnostics
    for t in ["diag a", "diag b", "diag c"]:
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {"task": t, "importance": 1, "memory_type": "episodic"},
            },
        )
        assert r.status_code == 200

    r = client.get("/micro/diag")
    assert r.status_code == 200
    data = r.json()
    assert data.get("enabled") is True
    assert isinstance(data.get("columns", {}), dict)
    print("Micro diag test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
