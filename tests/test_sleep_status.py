import os
import sys
from importlib import import_module


def _fresh_app_with_env(env: dict):
    os.environ.update(env)
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    return app_mod.app


def test_sleep_status_shape():
    env = {
        "SOMABRAIN_CONSOLIDATION_ENABLED": "true",
        "SOMABRAIN_SLEEP_INTERVAL_SECONDS": "0",
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT": "",
        "SOMABRAIN_REQUIRE_MEMORY": "0",
        "SOMABRAIN_STRICT_REAL": "0",
    }
    app = _fresh_app_with_env(env)
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.get("/sleep/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data and "interval_seconds" in data and "last" in data
