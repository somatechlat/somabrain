from importlib import import_module

from fastapi.testclient import TestClient


def test_migrate_import_wm_warming_counts():
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Prepare a minimal import payload with only WM items
    wm_items = [
        {"task": "warm wm item 1", "importance": 1, "memory_type": "episodic"},
        {"task": "warm wm item 2", "importance": 1, "memory_type": "episodic"},
    ]
    payload = {"manifest": {"version": 1}, "memories": [], "wm": wm_items}

    r = client.post("/migrate/import", json=payload)
    if r.status_code == 404:
        return  # minimal API mode; endpoint intentionally hidden
    assert r.status_code == 200
    data = r.json()
    assert data.get("imported") == 0
    assert data.get("wm_warmed") == len(wm_items)

    # Also ensure /metrics contains the wm admit counter series (at least once
    # from warming)
    m = client.get("/metrics")
    assert m.status_code == 200
    assert "somabrain_wm_admit_total" in m.text
