import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Seed some episodics
    for i in range(3):
        r = client.post(
            "/remember",
            json={
                "coord": None,
                "payload": {
                    "task": f"mig task {i}",
                    "importance": 1,
                    "memory_type": "episodic",
                },
            },
        )
        assert r.status_code == 200

    # Export with WM
    r = client.post("/migrate/export", json={"include_wm": True, "wm_limit": 16})
    assert r.status_code == 200
    exp = r.json()
    assert "manifest" in exp and "memories" in exp

    # Import back (no replace semantics yet)
    r = client.post(
        "/migrate/import",
        json={
            "manifest": exp["manifest"],
            "memories": exp["memories"],
            "wm": exp.get("wm", []),
        },
    )
    assert r.status_code == 200
    imp = r.json()
    assert "imported" in imp and "wm_warmed" in imp
    print("Migration test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
