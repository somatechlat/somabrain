"""
Tests for the non-minimal /metrics/snapshot JSON endpoint and WM admissions metric.
"""

from importlib import import_module

from fastapi.testclient import TestClient


def test_metrics_snapshot_and_wm_admit_counter():
    app_mod = import_module("somabrain.app")
    app = app_mod.app

    client = TestClient(app)

    # Prime a memory to trigger a WM admit from /remember
    r = client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {
                "task": "metric test",
                "importance": 1,
                "memory_type": "episodic",
            },
        },
    )
    assert r.status_code == 200

    # Snapshot should be available (non-minimal API only). If minimal, skip.
    # We detect minimal by checking for 404.
    r = client.get("/metrics/snapshot")
    if r.status_code == 404:
        return  # minimal public API mode; endpoint intentionally hidden
    assert r.status_code == 200
    data = r.json()
    assert "api_version" in data and "attention_level" in data

    # Verify Prometheus metrics includes the wm admit counter series
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "somabrain_wm_admit_total" in text
